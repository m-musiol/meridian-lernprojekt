"""Einzelne Datenqualitaets-/Eignungschecks fuer Stufe 2 (Gate 1).

Jeder Check liefert ein CheckResult mit Ampel-Status (gruen/gelb/rot), einer kurzen
Zusammenfassung des Messwerts, der Begruendung des Schwellenwerts und ggf. einer
Handlungsempfehlung. Schwellenwerte sind bewusst als grobe, dokumentierte Faustregeln
gewaehlt (kein Hard-Cutoff aus der Meridian-Doku), siehe docs/wissensbasis_pipeline.md
Abschnitt 2, Stufe 2.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

EXPECTED_CONTROLS = (
    "price_index", "promo_flag", "holiday_flag",
    "temperature_c", "consumer_climate_index", "competitor_spend_proxy_eur",
)


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


def _geo_week_spend_per_capita_matrix(media_df: pd.DataFrame, geo_df: pd.DataFrame) -> pd.DataFrame:
    """Kanal-Spend pro Kopf je (Geo, Woche)-Beobachtung — die Granularitaet, auf der Meridian

    tatsaechlich schaetzt. Ohne Pro-Kopf-Normalisierung korrelieren praktisch alle Kanaele stark
    miteinander, weil grosse Geos bei jedem Kanal automatisch mehr ausgeben als kleine — das ist
    reiner Groesseneffekt, keine echte Kollinearitaet, und wuerde den Check unbrauchbar machen.
    """
    merged = media_df.merge(geo_df[["geo", "population"]], on="geo")
    merged["spend_per_capita"] = merged["spend_eur"] / merged["population"]
    return merged.pivot_table(index=["geo", "time"], columns="channel", values="spend_per_capita").fillna(0)


def _compute_vif(national_df: pd.DataFrame) -> dict:
    cols = list(national_df.columns)
    x_full = national_df.to_numpy()
    vif = {}
    for i, col in enumerate(cols):
        y = x_full[:, i]
        x_others = np.delete(x_full, i, axis=1)
        x_design = np.column_stack([np.ones(len(y)), x_others])
        coefs, *_ = np.linalg.lstsq(x_design, y, rcond=None)
        y_hat = x_design @ coefs
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        vif[col] = 1 / (1 - r2) if r2 < 0.999 else float("inf")
    return vif


def check_collinearity(media_df: pd.DataFrame, geo_df: pd.DataFrame) -> CheckResult:
    geo_week = _geo_week_spend_per_capita_matrix(media_df, geo_df)
    corr = geo_week.corr()
    np.fill_diagonal(corr.values, 0)
    max_corr = corr.values.max()
    max_pair = corr.stack().idxmax()
    vif = _compute_vif(geo_week)
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


def check_outliers_and_units(media_df: pd.DataFrame, controls_kpi_df: pd.DataFrame) -> CheckResult:
    negative_spend = int((media_df["spend_eur"] < 0).sum())
    negative_kpi = int((controls_kpi_df[["revenue_eur", "website_sessions"]] < 0).sum().sum())

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


def check_controls_availability(controls_kpi_df: pd.DataFrame) -> CheckResult:
    missing_cols = [c for c in EXPECTED_CONTROLS if c not in controls_kpi_df.columns]
    if missing_cols:
        status = "rot"
        null_info = "n/a"
    else:
        null_shares = controls_kpi_df[list(EXPECTED_CONTROLS)].isna().mean()
        status = "gruen" if null_shares.max() < 0.02 else "gelb"
        null_info = f"max. Lueckenanteil {null_shares.max():.1%}"
    return CheckResult(
        name="Verfuegbarkeit Kontrollvariablen",
        status=status,
        summary=f"Fehlende Spalten: {missing_cols or 'keine'}. {null_info}.",
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


def check_reach_frequency(media_df: pd.DataFrame, expected_rf_channels: tuple) -> CheckResult:
    coverage = {}
    for channel in expected_rf_channels:
        sub = media_df[media_df["channel"] == channel]
        coverage[channel] = bool("reach" in sub.columns and sub["reach"].notna().any())
    status = "gruen" if all(coverage.values()) else "gelb"
    return CheckResult(
        name="Reach/Frequency-Verfuegbarkeit",
        status=status,
        summary=f"Abdeckung je erwartetem R/F-Kanal: {coverage}.",
        reasoning="Stakeholder-Briefing verlangt mind. 2 Kanaele mit Reach/Frequency fuer die "
        "feinere Frequenzmodellierung.",
        recommendation="" if status == "gruen" else "Fehlende R/F-Daten ergaenzen oder Kanal ohne R/F modellieren.",
    )
