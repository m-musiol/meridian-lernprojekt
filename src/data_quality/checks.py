"""Einzelne Datenqualitaets-/Eignungschecks fuer Stufe 2 (Gate 1).

Jeder Check liefert ein CheckResult mit Ampel-Status (gruen/gelb/rot), einer kurzen
Zusammenfassung des Messwerts, der Begruendung des Schwellenwerts und ggf. einer
Handlungsempfehlung. Schwellenwerte sind bewusst als grobe, dokumentierte Faustregeln
gewaehlt (kein Hard-Cutoff aus der Meridian-Doku), siehe docs/wissensbasis_pipeline.md
Abschnitt 2, Stufe 2.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ auf den Pfad
from data_quality.geo_normalization import compute_vif, geo_week_spend_per_capita_matrix

# Reserviert fuer die Auto-Erkennung von Kontrollvariablen (alles ausser diesen + KPI-Spalten
# in controls_kpi.csv gilt als Control) — siehe check_controls_availability.
RESERVED_NON_CONTROL_COLUMNS = ("geo", "time", "population")


@dataclass
class CheckResult:
    name: str
    status: str  # "gruen", "gelb", "rot"
    summary: str
    reasoning: str
    recommendation: str = ""


def check_completeness(media_df: pd.DataFrame) -> CheckResult:
    missing_share = media_df.groupby("channel")["spend_eur"].apply(lambda s: s.isna().mean())
    worst = missing_share.max()
    affected = {k: round(v, 3) for k, v in missing_share[missing_share > 0].to_dict().items()}
    if worst < 0.02:
        status = "gruen"
    elif worst <= 0.10:
        status = "gelb"
    else:
        status = "rot"
    return CheckResult(
        name="Vollstaendigkeit (fehlende Wochen je Kanal)",
        status=status,
        summary=f"Groesste Luecke: {worst:.1%}. Betroffene Kanaele: {affected or 'keine'}.",
        reasoning="Faustregel: <2% gruen (vernachlaessigbar), 2-10% gelb (dokumentieren/imputieren), "
        ">10% rot (Kanal ggf. ausschliessen oder Daten nachliefern).",
        recommendation="" if status == "gruen" else
        "Fehlende Wochen vor Stufe 4 explizit behandeln (Interpolation oder Null-Fill mit Flag) "
        "und als Limitierung in der Model Card vermerken.",
    )


def check_granularity(media_df: pd.DataFrame, controls_kpi_df: pd.DataFrame, geo_df: pd.DataFrame) -> CheckResult:
    times = pd.to_datetime(media_df["time"]).drop_duplicates().sort_values()
    deltas = times.diff().dropna().unique()
    weekly_ok = all(pd.Timedelta(d) == pd.Timedelta(days=7) for d in deltas)
    known_geos = set(geo_df["geo"])
    geo_ok = set(media_df["geo"]).issubset(known_geos) and set(controls_kpi_df["geo"]).issubset(known_geos)
    status = "gruen" if weekly_ok and geo_ok else "rot"
    return CheckResult(
        name="Granularitaet (Wochenebene, Geo-Zuordnung)",
        status=status,
        summary=f"Wochentakt durchgehend: {weekly_ok}. Alle Geos bekannt: {geo_ok}.",
        reasoning="Meridian erwartet konsistente Zeit- und Geo-Achsen; unregelmaessige Zeitschritte oder "
        "unbekannte Geos machen das Input-Array-Mapping (Stufe 4) unmoeglich.",
        recommendation="" if status == "gruen" else "Zeit-/Geo-Inkonsistenzen vor Stufe 4 beheben.",
    )


def check_time_vs_complexity(n_geos: int, n_weeks: int, n_channels: int, n_controls: int) -> CheckResult:
    observations = n_geos * n_weeks
    estimated_knots = max(1, round(n_weeks / 8))  # grobe Heuristik: ca. 1 Knoten je 2 Monate
    param_count = n_channels + n_controls + estimated_knots
    ratio = observations / param_count
    if ratio > 20:
        status = "gruen"
    elif ratio >= 10:
        status = "gelb"
    else:
        status = "rot"
    return CheckResult(
        name="Zeitraumlaenge vs. Modellkomplexitaet",
        status=status,
        summary=f"{observations} Beobachtungen (Geos x Wochen) vs. ca. {param_count} Parameter "
        f"({n_channels} Kanaele + {n_controls} Controls + {estimated_knots} geschaetzte Knots) "
        f"= Verhaeltnis {ratio:.1f}.",
        reasoning="Grobe Faustregel aus der Meridian-Doku (kein Hard-Cutoff): Verhaeltnis >20 gruen "
        "(komfortabel), 10-20 gelb (machbar, aber wenig Puffer fuer Geo-Hierarchie-Varianz), <10 rot "
        "(Ueberparametrisierung wahrscheinlich, Konvergenzprobleme zu erwarten).",
        recommendation="" if status == "gruen" else
        "Knot-Zahl niedrig halten oder Geo-Anzahl/Zeitraum in Stufe 1 erhoehen, siehe Stufe 5.",
    )


def check_spend_variance(media_df: pd.DataFrame) -> CheckResult:
    stats = media_df.groupby("channel")["spend_eur"].agg(["mean", "std"])
    stats["cv"] = stats["std"] / stats["mean"]
    worst_channel = stats["cv"].idxmin()
    worst_cv = stats["cv"].min()
    if worst_cv > 0.3:
        status = "gruen"
    elif worst_cv >= 0.15:
        status = "gelb"
    else:
        status = "rot"
    return CheckResult(
        name="Spend-Varianz je Kanal (Variationskoeffizient)",
        status=status,
        summary=f"Niedrigster Variationskoeffizient: {worst_channel} mit CV={worst_cv:.2f}.",
        reasoning="Faustregel: CV>0.3 gruen (genug Schwankung, um den Kanaleffekt vom Rauschen zu "
        "trennen), 0.15-0.3 gelb, <0.15 rot (nahezu konstanter Spend erschwert Identifikation der "
        "Saettigungskurve).",
        recommendation="" if status == "gruen" else
        f"Fuer {worst_channel}: Spend-Schwankung pruefen (z.B. bewusste Flighting-Perioden), sonst "
        "Priors in Stufe 5 enger fassen, um Nichtidentifizierbarkeit abzufedern.",
    )


def check_collinearity(media_df: pd.DataFrame, geo_df: pd.DataFrame) -> CheckResult:
    geo_week = geo_week_spend_per_capita_matrix(media_df, geo_df)
    corr = geo_week.corr()
    # .where() statt np.fill_diagonal(corr.values, ...): neuere pandas/numpy-Kombinationen geben aus
    # .values teils ein read-only Array zurueck, an dem eine In-Place-Zuweisung fehlschlaegt.
    corr = corr.where(~np.eye(len(corr), dtype=bool), 0.0)
    max_corr = corr.values.max()
    max_pair = corr.stack().idxmax()
    vif = compute_vif(geo_week)
    worst_channel = max(vif, key=vif.get)
    worst_vif = vif[worst_channel]
    if worst_vif < 5:
        status = "gruen"
    elif worst_vif <= 10:
        status = "gelb"
    else:
        status = "rot"
    return CheckResult(
        name="Kollinearitaet zwischen Kanaelen (Korrelation/VIF)",
        status=status,
        summary=f"Hoechste Korrelation: {max_pair[0]}<->{max_pair[1]} = {max_corr:.2f}. "
        f"Hoechster VIF: {worst_channel} = {worst_vif:.1f}.",
        reasoning="Berechnet auf Geo-Wochen-Ebene pro Kopf (nicht national aggregiert, nicht in "
        "absoluten EUR), da absolute Spend-Werte sonst nur den Geo-Groesseneffekt messen wuerden statt "
        "echter zeitlicher Kollinearitaet. Faustregel VIF: <5 gruen, 5-10 gelb (beobachten), >10 rot "
        "(klassischer Schwellenwert fuer problematische Multikollinearitaet — der Kanaleffekt laesst "
        "sich kaum noch vom korrelierten Nachbarkanal trennen).",
        recommendation="" if status == "gruen" else
        f"{worst_channel}: engere/informativere Priors in Stufe 5 in Erwaegung ziehen oder Kanaele "
        "ggf. zu einer Kanalgruppe zusammenfassen, da die Einzelwirkung datenseitig kaum trennbar ist.",
    )


def check_outliers_and_units(
    media_df: pd.DataFrame, controls_kpi_df: pd.DataFrame, kpi_columns: tuple[str, ...]
) -> CheckResult:
    negative_spend = int((media_df["spend_eur"] < 0).sum())
    negative_kpi = int((controls_kpi_df[list(kpi_columns)] < 0).sum().sum())

    outlier_counts = {}
    for channel, group in media_df.groupby("channel"):
        s = group["spend_eur"].dropna()
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - 3 * iqr, q3 + 3 * iqr
        outlier_counts[channel] = int(((s < lower) | (s > upper)).sum())
    total_outliers = sum(outlier_counts.values())
    outlier_share = total_outliers / len(media_df)

    if negative_spend == 0 and negative_kpi == 0 and outlier_share < 0.01:
        status = "gruen"
    elif negative_spend == 0 and negative_kpi == 0 and outlier_share < 0.03:
        status = "gelb"
    else:
        status = "rot"
    return CheckResult(
        name="Ausreisser & Einheiten-Konsistenz",
        status=status,
        summary=f"Negativer Spend: {negative_spend}, negative KPI-Werte: {negative_kpi}, "
        f"IQR-Ausreisser (>3x IQR): {total_outliers} von {len(media_df)} Zeilen ({outlier_share:.1%}).",
        reasoning="Negative Spend-/KPI-Werte sind ein Hard-Fail (Einheiten-Inkonsistenz). Ausreisser-Anteil "
        "per 3x-IQR-Regel: <1% gruen, 1-3% gelb (pruefen, meist echte Kampagnenspitzen), >3% rot.",
        recommendation="" if status == "gruen" else "Ausreisser-Zeilen manuell pruefen (echte Spitze vs. Messfehler).",
    )


def check_controls_availability(
    controls_kpi_df: pd.DataFrame,
    expected_controls: tuple[str, ...] | None = None,
    kpi_columns: tuple[str, ...] = (),
) -> CheckResult:
    """`expected_controls=None` => aus den Daten ableiten (alle Spalten ausser geo/time/population/KPIs) —

    noetig fuer hochgeladene Kunden, die keine explizite Kontrollvariablen-Liste deklarieren.
    """
    auto_detected = expected_controls is None
    if auto_detected:
        reserved = set(RESERVED_NON_CONTROL_COLUMNS) | set(kpi_columns)
        expected_controls = tuple(c for c in controls_kpi_df.columns if c not in reserved)

    missing_cols = [c for c in expected_controls if c not in controls_kpi_df.columns]
    if missing_cols:
        status = "rot"
        null_info = "n/a"
    else:
        null_shares = controls_kpi_df[list(expected_controls)].isna().mean()
        status = "gruen" if null_shares.max() < 0.02 else "gelb"
        null_info = f"max. Lueckenanteil {null_shares.max():.1%}"
    detection_note = " (automatisch erkannt)" if auto_detected else ""
    return CheckResult(
        name="Verfuegbarkeit Kontrollvariablen",
        status=status,
        summary=f"Controls{detection_note}: {list(expected_controls)}. Fehlende Spalten: "
        f"{missing_cols or 'keine'}. {null_info}.",
        reasoning="Kontrollvariablen sind noetig, um Confounder (z.B. Preis, Promotion, Saisonalitaet) "
        "von der Media-Wirkung zu trennen — ohne sie droht Overattribution auf Media.",
        recommendation="" if status == "gruen" else "Fehlende/luecken­hafte Controls vor Stufe 5 ergaenzen.",
    )


def check_geo_population(geo_df: pd.DataFrame, expected_n_geos: int) -> CheckResult:
    has_all = len(geo_df) == expected_n_geos
    positive = bool((geo_df["population"] > 0).all())
    status = "gruen" if has_all and positive else "rot"
    return CheckResult(
        name="Geo-Populationsdaten",
        status=status,
        summary=f"{len(geo_df)}/{expected_n_geos} Geos mit Populationswert, alle positiv: {positive}.",
        reasoning="Pflicht fuer ein Geo-Modell — Meridian nutzt die Population zur Skalierung von "
        "Baseline und Kanaleffekten zwischen Geos.",
        recommendation="" if status == "gruen" else "Fehlende/ungueltige Populationswerte vor Stufe 4 ergaenzen.",
    )


def check_reach_frequency(media_df: pd.DataFrame, expected_rf_channels: tuple[str, ...] | None = None) -> CheckResult:
    """`expected_rf_channels=None` => aus den Daten ableiten (alle Kanaele mit befuellter reach-Spalte) —

    noetig fuer hochgeladene Kunden, bei denen vorab nicht bekannt ist, welche Kanaele R/F liefern.
    """
    if expected_rf_channels is None:
        has_reach = "reach" in media_df.columns
        detected = tuple(
            ch for ch in media_df["channel"].unique()
            if has_reach and media_df.loc[media_df["channel"] == ch, "reach"].notna().any()
        )
        return CheckResult(
            name="Reach/Frequency-Verfuegbarkeit",
            status="gruen",
            summary=f"Automatisch erkannte R/F-Kanaele: {list(detected) or 'keine'}.",
            reasoning="Keine vordeklarierte Kanalliste vorhanden — es wird nur berichtet, welche "
            "Kanaele tatsaechlich Reach/Frequency-Daten liefern.",
            recommendation="",
        )

    coverage = {}
    for channel in expected_rf_channels:
        sub = media_df[media_df["channel"] == channel]
        coverage[channel] = bool("reach" in sub.columns and sub["reach"].notna().any())
    status = "gruen" if all(coverage.values()) else "gelb"
    return CheckResult(
        name="Reach/Frequency-Verfuegbarkeit",
        status=status,
        summary=f"Abdeckung je erwartetem R/F-Kanal: {coverage}.",
        reasoning="Client-Config verlangt Reach/Frequency fuer diese Kanaele (feinere Frequenzmodellierung).",
        recommendation="" if status == "gruen" else "Fehlende R/F-Daten ergaenzen oder Kanal ohne R/F modellieren.",
    )
