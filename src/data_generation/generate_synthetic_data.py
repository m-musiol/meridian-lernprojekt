"""Generiert einen synthetischen Datensatz fuer einen konfigurierten Kunden (Datenquelle 2, Stufe 1).

Erzeugt Media-, Kontroll- und KPI-Daten gemaess der jeweiligen `clients/<client_id>/config.py`
(siehe `src/client_config.py`). Alle wahren Effektstaerken (Adstock, Saettigung, ROI,
Kontroll-Koeffizienten) werden als Ground Truth gespeichert, um Modell-Ergebnisse spaeter
dagegen zu validieren (Stufe 8).

Deterministisch ueber --seed; alle Stellschrauben (Geo-Zahl, Zeitraum, Rausch-Intensitaet,
fehlende Wochen) sind per Client-Config vorgegeben und einzeln per CLI ueberschreibbar,
siehe --help. Die Kontrollvariablen-/Organic-Formeln (Preisindex, Wetter, Saisonalitaet, ...)
sind bewusst geteilte, generische Muster fuer alle synthetischen Demo-Kunden — keine
kundenspezifische Formelsprache, um das Projekt nicht zu einer Generator-DSL aufzublasen.
"""

import argparse
import dataclasses
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # src/ auf den Pfad
from client_config import ChannelConfig, ClientConfig, GeneratorSettings, load_client_config
from transforms import apply_adstock, hill_saturation


def make_time_index(cfg: GeneratorSettings) -> pd.DatetimeIndex:
    return pd.date_range(start=cfg.start_date, periods=cfg.n_weeks, freq="W-MON")


def make_geo_population(cfg: GeneratorSettings, rng: np.random.Generator) -> pd.DataFrame:
    raw_weights = rng.lognormal(mean=0.0, sigma=0.6, size=cfg.n_geos)
    shares = raw_weights / raw_weights.sum()
    population = shares * cfg.total_population
    geo_names = [f"Region_{i + 1:02d}" for i in range(cfg.n_geos)]
    return pd.DataFrame({"geo": geo_names, "population": population, "pop_share": shares})


def make_seasonal_multiplier(n_weeks: int) -> np.ndarray:
    """Zwei Nachfragespitzen: Jahresanfang (Neujahrs-Einrichtungsimpuls) und Q4 (Weihnachtsgeschaeft)."""
    week_of_year = np.arange(n_weeks) % 52
    q1_peak = 0.20 * np.exp(-0.5 * ((week_of_year - 3) / 4) ** 2)
    q4_peak = 0.30 * np.exp(-0.5 * ((week_of_year - 47) / 4) ** 2)
    return 1.0 + q1_peak + q4_peak


def make_holiday_flag(time_index: pd.DatetimeIndex) -> np.ndarray:
    week_of_year = time_index.isocalendar().week.to_numpy()
    return np.where((week_of_year >= 46) & (week_of_year <= 51), 1, 0)


def national_spend_series(
    channel: ChannelConfig, cfg: GeneratorSettings, seasonal: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    annual_budget = cfg.total_annual_media_budget_eur * channel.annual_budget_share
    base_weekly = annual_budget / 52.0
    # kanal-eigene Trendrichtung (nicht nur -staerke): manche Kanaele wachsen, andere schrumpfen
    # leicht ueber die 3 Jahre, sonst waeren ALLE Kanaele allein durch "beide steigen ueber die Zeit"
    # kuenstlich hochkorreliert, unabhaengig von der genauen Rate.
    trend_rate = rng.uniform(-0.0015, 0.003)
    trend = 1.0 + trend_rate * np.arange(cfg.n_weeks)
    channel_seasonal = jitter_seasonal(seasonal, rng)
    noise = rng.lognormal(mean=0.0, sigma=cfg.noise_sigma, size=cfg.n_weeks)
    return base_weekly * trend * channel_seasonal * noise


def jitter_seasonal(base_seasonal: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Leicht kanal-spezifische Verschiebung/Skalierung der saisonalen Nachfragekurve.

    Ohne diese Streuung wuerden alle Kanaele exakt im Gleichschritt schwanken (identische
    Kurvenform) und dadurch kuenstlich fast perfekt miteinander korrelieren — die bewusst
    eingebaute TV/Radio-Kollinearitaet (siehe derive_radio_spend) waere dann nicht mehr von
    dieser generischen "alle Kanaele teilen sich die Saison"-Korrelation zu unterscheiden.
    """
    phase_shift_weeks = int(rng.integers(-6, 7))  # Peak-Breite (Gauss-Sigma) ist 4 Wochen, Shift muss vergleichbar gross sein
    amplitude_scale = rng.uniform(0.5, 1.5)
    shifted = np.roll(base_seasonal - 1.0, phase_shift_weeks)
    return 1.0 + shifted * amplitude_scale


def split_across_geos(
    national_series: np.ndarray, geo_df: pd.DataFrame, rng: np.random.Generator
) -> np.ndarray:
    """(n_geos x n_weeks)-Matrix: Spend je Geo, gewichtet nach Bevoelkerung + Regions-Intensitaet."""
    raw_multiplier = rng.lognormal(mean=0.0, sigma=0.2, size=geo_df.shape[0])
    weighted_mean = np.sum(raw_multiplier * geo_df["pop_share"].to_numpy())
    geo_multiplier = raw_multiplier / weighted_mean  # haelt nationale Summe je Woche etwa konstant
    pop_share = geo_df["pop_share"].to_numpy().reshape(-1, 1)
    return national_series.reshape(1, -1) * pop_share * geo_multiplier.reshape(-1, 1)


def derive_radio_spend(
    tv_spend_geo: np.ndarray,
    channel: ChannelConfig,
    cfg: GeneratorSettings,
    seasonal: np.ndarray,
    geo_df: pd.DataFrame,
    rng: np.random.Generator,
) -> np.ndarray:
    """Radio behaelt sein eigenes Budget (annual_budget_share), aber die Verteilung ueber Geo/Zeit

    ist teils am TV-Muster ausgerichtet — Media-Planer takten beide Kanaele oft aehnlich, ohne dass
    dadurch automatisch mehr Geld fliesst. Das erzeugt echte, aber budgetneutrale Kollinearitaet
    (im Gegensatz zu einem simplen Aufschlag "on top", der Radios Budgetanteil verzerren wuerde).
    """
    own_spend_geo = split_across_geos(national_spend_series(channel, cfg, seasonal, rng), geo_df, rng)
    tv_shape = tv_spend_geo / tv_spend_geo.mean()
    own_shape = own_spend_geo / own_spend_geo.mean()

    tv_pattern_share = 0.9  # Anteil, zu dem Radios Verteilung dem TV-Muster folgt
    blended_shape = tv_pattern_share * tv_shape + (1 - tv_pattern_share) * own_shape
    noise = rng.lognormal(mean=0.0, sigma=0.05, size=tv_spend_geo.shape)
    return own_spend_geo.mean() * blended_shape * noise


def spend_to_impressions(
    spend_geo: np.ndarray, channel: ChannelConfig, rng: np.random.Generator
) -> np.ndarray:
    noise = rng.lognormal(mean=0.0, sigma=0.1, size=spend_geo.shape)
    return spend_geo / channel.cost_per_impression * noise


def split_reach_frequency(
    impressions_geo: np.ndarray, channel: ChannelConfig, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    frequency = channel.base_frequency * rng.lognormal(mean=0.0, sigma=0.1, size=impressions_geo.shape)
    frequency = np.clip(frequency, a_min=0.5, a_max=None)
    reach = impressions_geo / frequency
    return reach, frequency


def inject_missing_weeks(
    array_2d: np.ndarray, rate: float, rng: np.random.Generator
) -> np.ndarray:
    """Setzt je Geo zufaellig `rate` Anteil der Wochen auf NaN (simuliert Meldeluecken)."""
    result = array_2d.copy()
    n_geos, n_weeks = result.shape
    n_missing = int(round(rate * n_weeks))
    if n_missing == 0:
        return result
    for g in range(n_geos):
        missing_idx = rng.choice(n_weeks, size=n_missing, replace=False)
        result[g, missing_idx] = np.nan
    return result


def build_media_data(
    cfg: GeneratorSettings, rng: np.random.Generator, geo_df: pd.DataFrame, seasonal: np.ndarray
) -> dict:
    """Erzeugt Spend/Impressions/Reach/Frequency je Kanal als (n_geos x n_weeks)-Arrays."""
    media = {}
    tv_spend_geo = None
    for channel in cfg.channels:
        if channel.name == "Radio":
            spend_geo = derive_radio_spend(tv_spend_geo, channel, cfg, seasonal, geo_df, rng)
        else:
            national = national_spend_series(channel, cfg, seasonal, rng)
            spend_geo = split_across_geos(national, geo_df, rng)

        if channel.name == "TV":
            tv_spend_geo = spend_geo

        impressions_geo = spend_to_impressions(spend_geo, channel, rng)
        reach_geo, freq_geo = (None, None)
        if channel.has_reach_frequency:
            reach_geo, freq_geo = split_reach_frequency(impressions_geo, channel, rng)

        if channel.name in ("Out_of_Home", "Radio"):
            spend_geo = inject_missing_weeks(spend_geo, cfg.missing_week_rate, rng)
            impressions_geo = inject_missing_weeks(impressions_geo, cfg.missing_week_rate, rng)

        media[channel.name] = {
            "spend": spend_geo,
            "impressions": impressions_geo,
            "reach": reach_geo,
            "frequency": freq_geo,
        }
    return media


def compute_channel_contributions(
    media: dict, cfg: GeneratorSettings
) -> tuple[dict, dict, dict]:
    """Adstock + Hill-Saettigung je Kanal/Geo, kalibriert auf den Ziel-ROI bzw. Ziel-Sessions.

    Rueckgabe: (revenue_contrib, sessions_contrib, ground_truth) je Kanal.
    """
    revenue_contrib, sessions_contrib, ground_truth = {}, {}, {}
    for channel in cfg.channels:
        impressions = np.nan_to_num(media[channel.name]["impressions"], nan=0.0)
        adstocked = np.apply_along_axis(apply_adstock, 1, impressions, channel.adstock_decay)
        ec50 = channel.hill_ec50_share_of_max_exposure * adstocked.max()
        saturation = hill_saturation(adstocked, ec50, channel.hill_slope)

        spend = np.nan_to_num(media[channel.name]["spend"], nan=0.0)
        total_spend = spend.sum()
        total_saturation = saturation.sum()

        max_revenue_effect = channel.target_roi * total_spend / total_saturation
        max_sessions_effect = channel.target_sessions_per_1000_eur * (total_spend / 1000) / total_saturation

        revenue_contrib[channel.name] = max_revenue_effect * saturation
        sessions_contrib[channel.name] = max_sessions_effect * saturation
        ground_truth[channel.name] = {
            "adstock_decay": channel.adstock_decay,
            "hill_ec50": float(ec50),
            "hill_slope": channel.hill_slope,
            "target_roi": channel.target_roi,
            "realized_roi": float(revenue_contrib[channel.name].sum() / total_spend),
            "target_sessions_per_1000_eur": channel.target_sessions_per_1000_eur,
            "max_revenue_effect": float(max_revenue_effect),
            "max_sessions_effect": float(max_sessions_effect),
            "total_spend_eur": float(total_spend),
        }
    return revenue_contrib, sessions_contrib, ground_truth


def _channel_impressions_or_zero(media: dict, channel_name: str, n_geos: int, n_weeks: int) -> np.ndarray:
    """Impressions eines Kanals, falls vorhanden — sonst 0 (Kunde hat diesen Kanal evtl. nicht).

    Fuer Nordpunkt (hat beide Kanaele) unveraendertes Verhalten; erlaubt anderen Client-Configs
    ohne "Paid_Search_Brand"/"Paid_Social" einen graceful Fallback statt eines KeyError.
    """
    if channel_name not in media:
        return np.zeros((n_geos, n_weeks))
    return np.nan_to_num(media[channel_name]["impressions"], nan=0.0)


def generate_controls_and_organic(
    cfg: GeneratorSettings,
    rng: np.random.Generator,
    time_index: pd.DatetimeIndex,
    geo_df: pd.DataFrame,
    media: dict,
) -> pd.DataFrame:
    n_geos, n_weeks = cfg.n_geos, cfg.n_weeks
    holiday_flag = make_holiday_flag(time_index)
    promo_flag = (rng.random((n_geos, n_weeks)) < 0.10).astype(int)
    price_index = 100 + np.cumsum(rng.normal(0, 0.5, size=(n_geos, n_weeks)), axis=1)
    temperature = 10 + 8 * np.sin(2 * np.pi * (np.arange(n_weeks) - 13) / 52) + rng.normal(0, 1.5, (n_geos, n_weeks))
    consumer_climate = 0 + np.cumsum(rng.normal(0, 0.3, size=(n_geos, n_weeks)), axis=1)
    competitor_spend_proxy = (
        cfg.total_annual_media_budget_eur * 0.8 / 52 * geo_df["pop_share"].to_numpy().reshape(-1, 1)
        * rng.lognormal(0, 0.15, size=(n_geos, n_weeks))
    )
    organic_search_clicks = (
        1000 * geo_df["pop_share"].to_numpy().reshape(-1, 1) * (1 + 0.001 * np.arange(n_weeks))
        * rng.lognormal(0, 0.15, size=(n_geos, n_weeks))
        + 0.01 * _channel_impressions_or_zero(media, "Paid_Search_Brand", n_geos, n_weeks)
    )
    social_organic_reach = (
        2000 * geo_df["pop_share"].to_numpy().reshape(-1, 1)
        * rng.lognormal(0, 0.2, size=(n_geos, n_weeks))
        + 0.02 * _channel_impressions_or_zero(media, "Paid_Social", n_geos, n_weeks)
    )
    distribution_points = np.round(
        50 * geo_df["pop_share"].to_numpy().reshape(-1, 1) * (1 + 0.001 * np.arange(n_weeks))
    )
    assortment_breadth = np.tile(3000 + 2 * np.arange(n_weeks), (n_geos, 1))

    frames = []
    for i, geo in enumerate(geo_df["geo"]):
        frames.append(pd.DataFrame({
            "geo": geo,
            "time": time_index,
            "population": geo_df.loc[i, "population"],
            "price_index": price_index[i],
            "promo_flag": promo_flag[i],
            "holiday_flag": holiday_flag,
            "temperature_c": temperature[i],
            "consumer_climate_index": consumer_climate[i],
            "competitor_spend_proxy_eur": competitor_spend_proxy[i],
            "organic_search_clicks": organic_search_clicks[i],
            "social_organic_reach": social_organic_reach[i],
            "distribution_points": distribution_points[i],
            "assortment_breadth_skus": assortment_breadth[i],
        }))
    return pd.concat(frames, ignore_index=True)


def generate_kpis(
    cfg: GeneratorSettings,
    rng: np.random.Generator,
    geo_df: pd.DataFrame,
    controls_df: pd.DataFrame,
    revenue_contrib: dict,
    sessions_contrib: dict,
    primary_kpi_column: str = "revenue_eur",
    secondary_kpi_column: str = "website_sessions",
) -> tuple[pd.DataFrame, dict]:
    n_geos, n_weeks = cfg.n_geos, cfg.n_weeks
    total_revenue_contrib = sum(revenue_contrib.values())
    total_sessions_contrib = sum(sessions_contrib.values())

    control_coefs = {
        "price_index": -800.0, "promo_flag": 15000.0, "holiday_flag": 25000.0,
        "consumer_climate_index": 400.0, "competitor_spend_proxy_eur": -0.02,
    }
    baseline_revenue_per_capita = 0.08
    baseline_revenue = baseline_revenue_per_capita * geo_df["population"].to_numpy().reshape(-1, 1)

    price_index = controls_df.pivot(index="geo", columns="time", values="price_index").to_numpy()
    promo_flag = controls_df.pivot(index="geo", columns="time", values="promo_flag").to_numpy()
    holiday_flag = controls_df.pivot(index="geo", columns="time", values="holiday_flag").to_numpy()
    climate = controls_df.pivot(index="geo", columns="time", values="consumer_climate_index").to_numpy()
    competitor = controls_df.pivot(index="geo", columns="time", values="competitor_spend_proxy_eur").to_numpy()

    control_effect_revenue = (
        control_coefs["price_index"] * (price_index - 100)
        + control_coefs["promo_flag"] * promo_flag
        + control_coefs["holiday_flag"] * holiday_flag
        + control_coefs["consumer_climate_index"] * climate
        + control_coefs["competitor_spend_proxy_eur"] * competitor
    )
    revenue_noise = rng.lognormal(mean=0.0, sigma=cfg.noise_sigma, size=(n_geos, n_weeks))
    revenue = np.clip(baseline_revenue + total_revenue_contrib + control_effect_revenue, a_min=0, a_max=None) * revenue_noise

    baseline_sessions = 0.002 * geo_df["population"].to_numpy().reshape(-1, 1)
    sessions_noise = rng.lognormal(mean=0.0, sigma=cfg.noise_sigma, size=(n_geos, n_weeks))
    sessions = np.clip(baseline_sessions + total_sessions_contrib, a_min=0, a_max=None) * sessions_noise

    time_index = controls_df["time"].unique()
    frames = []
    for i, geo in enumerate(geo_df["geo"]):
        frames.append(pd.DataFrame({
            "geo": geo, "time": time_index,
            primary_kpi_column: revenue[i], secondary_kpi_column: sessions[i],
        }))
    kpi_df = pd.concat(frames, ignore_index=True)

    kpi_ground_truth = {
        "baseline_revenue_per_capita_eur": baseline_revenue_per_capita,
        "baseline_sessions_per_capita": 0.002,
        "control_coefficients_revenue": control_coefs,
        "kpi_noise_sigma": cfg.noise_sigma,
    }
    return kpi_df, kpi_ground_truth


def media_to_long_df(media: dict, geo_df: pd.DataFrame, time_index: pd.DatetimeIndex) -> pd.DataFrame:
    frames = []
    for channel_name, arrays in media.items():
        for i, geo in enumerate(geo_df["geo"]):
            frame = pd.DataFrame({
                "geo": geo, "time": time_index, "channel": channel_name,
                "spend_eur": arrays["spend"][i], "impressions": arrays["impressions"][i],
            })
            if arrays["reach"] is not None:
                frame["reach"] = arrays["reach"][i]
                frame["frequency"] = arrays["frequency"][i]
            frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def compute_noise_layer_metrics(media_df: pd.DataFrame, geo_df: pd.DataFrame) -> dict:
    """Fehlende-Wochen-Anteil je Kanal und die staerkste Kanal-Spend-Korrelation (pro Kopf, Geo-Wochen).

    Generisch gehalten (sucht die staerkste Korrelation, statt einen Kanalnamen wie "TV"/"Radio"
    hart zu codieren), damit es fuer jede Client-Config funktioniert, nicht nur fuer Nordpunkt.
    Pro-Kopf-Normalisierung ist noetig: in absoluten EUR wuerde die Korrelation ueberwiegend den
    Geo-Groesseneffekt messen (grosse Geos geben bei JEDEM Kanal mehr aus), nicht echte zeitliche
    Kollinearitaet. Gleiche Methodik wie src/data_quality/checks.py, damit beide Berichte konsistent sind.
    """
    missing_share = media_df.groupby("channel")["spend_eur"].apply(lambda s: s.isna().mean())
    affected_channels = missing_share[missing_share > 0]

    merged = media_df.merge(geo_df[["geo", "population"]], on="geo")
    merged["spend_per_capita"] = merged["spend_eur"] / merged["population"]
    wide = merged.pivot_table(index=["geo", "time"], columns="channel", values="spend_per_capita").fillna(0)
    corr = wide.corr()
    np.fill_diagonal(corr.values, 0)

    highest_pair = corr.stack().idxmax()
    highest_corr = corr.values.max()

    corr_without_highest = corr.copy()
    corr_without_highest.loc[highest_pair[0], highest_pair[1]] = 0
    corr_without_highest.loc[highest_pair[1], highest_pair[0]] = 0
    second_pair = corr_without_highest.stack().idxmax()
    second_corr = corr_without_highest.values.max()

    return {
        "missing_share_by_channel": affected_channels.to_dict(),
        "highest_pair": highest_pair,
        "highest_correlation": highest_corr,
        "second_pair": second_pair,
        "second_correlation": second_corr,
    }


def compute_kpi_summary(controls_kpi_df: pd.DataFrame, kpi_columns: tuple[str, ...]) -> dict:
    summary = {}
    for col in kpi_columns:
        series = controls_kpi_df[col]
        summary[col] = {
            "min": series.min(), "median": series.median(),
            "mean": series.mean(), "max": series.max(),
        }
    return summary


def write_report(
    output_dir: pathlib.Path,
    ground_truth_dir: pathlib.Path,
    cfg: GeneratorSettings,
    channel_gt: dict,
    media_df: pd.DataFrame,
    controls_kpi_df: pd.DataFrame,
    geo_df: pd.DataFrame,
    client: ClientConfig,
) -> None:
    noise_metrics = compute_noise_layer_metrics(media_df, geo_df)
    kpi_columns = (client.primary_kpi_column, client.secondary_kpi_column)
    kpi_summary = compute_kpi_summary(controls_kpi_df, kpi_columns)

    lines = [
        f"# Stufe 1 — Bericht: Synthetischer Datensatz ({client.display_name}, Datenquelle 2)\n",
        "Dieser Bericht wird automatisch bei jedem Lauf von `generate_synthetic_data.py` neu erzeugt "
        "(nicht von Hand editieren — Aenderungen bitte im Skript vornehmen, siehe `write_report()`).\n",
        "## 1. Erzeugungs-Parameter (Stellschrauben)\n",
        "Diese Werte werden beim Aufruf des Skripts per CLI-Flag gesetzt (siehe `--help`) und "
        "bestimmen Umfang und Schwierigkeitsgrad der generierten Daten:\n",
        f"- **Seed:** `{cfg.seed}` — Startwert des Zufallsgenerators. Gleicher Seed + gleiche Parameter "
        "= exakt reproduzierbare Daten (Pflicht laut `CLAUDE.md`, Punkt 7).",
        f"- **Geos:** {cfg.n_geos} — Anzahl simulierter Regionen. Mehr Geos = mehr Beobachtungen fuer "
        "die spaetere Modellschaetzung, aber auch mehr Parameter (siehe Gate-1-Heuristik in Stufe 2).",
        f"- **Wochen:** {cfg.n_weeks} — Laenge der Zeitreihe. Zu kurz erschwert es, langsam wirkende "
        "Adstock-Effekte (z.B. TV) und Jahressaisonalitaet ueberhaupt zu erkennen.",
        f"- **Start:** {cfg.start_date} — erster Wochenmontag der Zeitreihe.",
        f"- **Jahresbudget:** {cfg.total_annual_media_budget_eur:,.0f} {client.currency} — nationales "
        "Media-Gesamtbudget pro Jahr, auf die Kanaele gemaess `annual_budget_share` in der "
        f"Client-Config (`clients/{client.client_id}/config.py`) aufgeteilt.",
        "\n## 2. Kanal-Kennzahlen: Ground Truth\n",
        "\"Ground Truth\" heisst hier: die *wahren*, beim Generieren fest vorgegebenen Effektstaerken — "
        "in echten Projekten unbekannt, hier bewusst bekannt, um spaeter (Stufe 8) zu pruefen, ob das "
        "trainierte Meridian-Modell sie aus den Daten korrekt zurueckgewinnt (\"Parameter Recovery\").\n",
        "| Kanal | Spend gesamt (EUR) | Ziel-ROI | realisierter ROI | Adstock-Decay | Hill-Slope | Hill-EC50 |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, gt in channel_gt.items():
        lines.append(
            f"| {name} | {gt['total_spend_eur']:,.0f} | {gt['target_roi']:.2f} | {gt['realized_roi']:.2f} | "
            f"{gt['adstock_decay']:.2f} | {gt['hill_slope']:.2f} | {gt['hill_ec50']:,.0f} |"
        )

    lines += [
        "\n### Wie werden diese Kennzahlen berechnet, und was sagen sie aus?\n",
        "- **Spend gesamt:** Summe von `spend_eur` ueber alle Geos und Wochen (fehlende Wochen zaehlen "
        "als 0). Zeigt die Groessenordnung des Kanals im Media-Mix.",
        "- **Adstock-Decay** (0–1): woechentliche \"Retention-Rate\" der Werbewirkung. Formel: "
        "`adstocked[t] = exposure[t] + decay * adstocked[t-1]` (siehe `transforms.apply_adstock`). "
        "Ein Wert von 0,6 (TV) bedeutet: 60 % der Wirkung einer Woche schwappen in die Folgewoche "
        "rueber, bei 0,1 (Paid Search Brand) ist der Effekt fast schon nach einer Woche verpufft — "
        "Suchintention ist kurzlebig, TV-Markenwirkung haelt laenger an.",
        "- **Hill-Slope & Hill-EC50:** beschreiben gemeinsam die Saettigungskurve "
        "`saturation = adstocked^slope / (adstocked^slope + ec50^slope)` (siehe "
        "`transforms.hill_saturation`), Ergebnis zwischen 0 und 1. `Hill-EC50` ist der "
        "Halbsaettigungspunkt: bei diesem (adstockten) Exposure-Niveau ist bereits 50 % der maximal "
        "moeglichen Kanalwirkung erreicht — je hoeher der bisherige Spend im Verhaeltnis zum EC50, "
        "desto staerker die abnehmenden Grenzertraege. `Hill-Slope` steuert, wie abrupt dieser "
        "Uebergang von \"linear wachsend\" zu \"gesaettigt\" verlaeuft (hoeherer Wert = schaerferer Knick).",
        "- **Ziel-ROI vs. realisierter ROI:** `Ziel-ROI` ist die in `config.py` vorgegebene Wunsch-Kennzahl "
        "(Umsatz in EUR je ausgegebenem Euro). Waehrend der Generierung wird daraus ein Skalierungsfaktor "
        "(`max_revenue_effect`) berechnet, mit dem die Saettigungskurve so skaliert wird, dass "
        "`realisierter ROI = Summe(Umsatzbeitrag) / Summe(Spend)` moeglichst genau dem Ziel entspricht "
        "(siehe `compute_channel_contributions`). Beide Werte sollten daher (fast) identisch sein — "
        "eine spuerbare Abweichung waere ein Hinweis auf einen Rechenfehler in der Kalibrierung.",
        "\n## 3. Bewusster Noise-Layer (relevant fuer Stufe 2)\n",
        "Reale Mediadaten sind nie perfekt — deshalb baut der Generator zwei typische Praxisprobleme "
        "absichtlich ein, damit die Datenqualitaetspruefung in Stufe 2 nicht trivial \"gruen\" ausfaellt:\n",
    ]

    for channel_name, share in noise_metrics["missing_share_by_channel"].items():
        lines.append(
            f"- **Fehlende Wochen bei {channel_name}:** {share:.1%} der Geo-Wochen sind `NaN` "
            "(zufaellig je Geo ausgewaehlt, simuliert unvollstaendige Kanal-Meldungen/Datenlieferung)."
        )
    highest_pair = noise_metrics["highest_pair"]
    highest_corr = noise_metrics["highest_correlation"]
    second_pair = noise_metrics["second_pair"]
    second_corr = noise_metrics["second_correlation"]
    lines.append(
        f"- **Staerkste Kanal-Spend-Korrelation:** {highest_pair[0]}↔{highest_pair[1]} = {highest_corr:.3f} "
        "(Pearson-Korrelation des Spends pro Kopf je Geo-Woche — absolute EUR-Werte wuerden vor allem "
        "den Geo-Groesseneffekt messen, siehe `compute_noise_layer_metrics`). Falls einer der beiden "
        "Kanaele bewusst am Muster des anderen ausgerichtet ist (siehe `derive_radio_spend` fuer ein "
        "Beispiel dieser Technik), ist das Absicht: Media-Planer takten verwandte Kanaele in der "
        "Praxis oft gemeinsam, was es einem Modell erschwert, die Einzelwirkung sauber zu trennen "
        f"(Multikollinearitaet, klassischer VIF-Kandidat in Stufe 2). Naechsthoechstes Kanalpaar: "
        f"{second_pair[0]}↔{second_pair[1]} = {second_corr:.3f} — spuerbar niedriger, da dort nur die "
        "gemeinsame (leicht kanal-spezifisch verschobene) Saisonalitaet durchschlaegt, nicht die "
        "gezielte Kopplung.",
    )

    lines += [
        "\n## 4. Verteilung der Zielgroessen (KPIs)\n",
        "Werte je Geo-Woche, nach der Kombination aus Baseline + Kanalbeitraegen + Kontrolleffekten + "
        "multiplikativem Messrauschen (`noise_sigma`):\n",
        "| KPI | Minimum | Median | Mittelwert | Maximum |",
        "|---|---|---|---|---|",
    ]
    for col in kpi_columns:
        s = kpi_summary[col]
        label = col.removesuffix("_eur").replace("_", " ").title()
        if col.endswith("_eur"):
            label += f" ({client.currency})"
        lines.append(f"| {label} | {s['min']:,.0f} | {s['median']:,.0f} | {s['mean']:,.0f} | {s['max']:,.0f} |")
    lines += [
        "\nKeine negativen Werte moeglich (durch `np.clip` vor dem Rauschen abgesichert). Die Spanne "
        "zwischen Minimum und Maximum entsteht durch die Kombination aus unterschiedlich grossen Geos "
        "(Bevoelkerung), Saisonalitaet (Q1-/Q4-Peaks) und den Media-/Kontrolleffekten — genau diese "
        "Variation braucht ein MMM-Modell spaeter, um Kanalwirkungen ueberhaupt schaetzen zu koennen.\n",
        "## 5. Ausgabedateien\n",
        f"- `{output_dir.as_posix()}/media.csv` — Spend/Impressions/Reach/Frequency je Geo, Woche, Kanal (Long-Format).",
        f"- `{output_dir.as_posix()}/controls_kpi.csv` — Controls, Organic-/Non-Media-Signale und beide KPIs je Geo/Woche.",
        f"- `{output_dir.as_posix()}/geo_population.csv` — Bevoelkerung und Bevoelkerungsanteil je Geo.",
        f"- `{ground_truth_dir.as_posix()}/{client.client_id}_ground_truth.json` — alle wahren Parameter "
        "maschinenlesbar (fuer den Modell-vs-Wahrheit-Vergleich in Stufe 8).",
    ]

    report_path = pathlib.Path(f"reports/{client.client_id}/stufe1_datengenerierung_bericht.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generiert einen synthetischen Datensatz fuer einen konfigurierten Kunden."
    )
    parser.add_argument("--client", default="nordpunkt", help="Client-ID unter clients/<id>/config.py")
    # Alle folgenden Flags ueberschreiben nur, wenn sie explizit gesetzt werden (sonst Client-Default).
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--n-geos", type=int, default=None)
    parser.add_argument("--n-weeks", type=int, default=None)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--annual-media-budget", type=float, default=None)
    parser.add_argument("--noise-sigma", type=float, default=None)
    parser.add_argument("--missing-week-rate", type=float, default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--ground-truth-dir", default=None)
    args = parser.parse_args()

    client = load_client_config(args.client)
    if client.data_source != "synthetic" or client.generator is None:
        raise ValueError(f"Client '{client.client_id}' hat data_source='{client.data_source}', braucht 'synthetic'.")

    overrides = {
        "seed": args.seed, "n_geos": args.n_geos, "n_weeks": args.n_weeks, "start_date": args.start_date,
        "total_annual_media_budget_eur": args.annual_media_budget, "noise_sigma": args.noise_sigma,
        "missing_week_rate": args.missing_week_rate,
    }
    overrides = {k: v for k, v in overrides.items() if v is not None}
    cfg = dataclasses.replace(client.generator, **overrides) if overrides else client.generator

    output_dir = pathlib.Path(args.output_dir or client.data_dir)
    ground_truth_dir = pathlib.Path(args.ground_truth_dir or client.ground_truth_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ground_truth_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(cfg.seed)
    time_index = make_time_index(cfg)
    geo_df = make_geo_population(cfg, rng)
    seasonal = make_seasonal_multiplier(cfg.n_weeks)

    media = build_media_data(cfg, rng, geo_df, seasonal)
    revenue_contrib, sessions_contrib, channel_ground_truth = compute_channel_contributions(media, cfg)
    controls_df = generate_controls_and_organic(cfg, rng, time_index, geo_df, media)
    kpi_df, kpi_ground_truth = generate_kpis(
        cfg, rng, geo_df, controls_df, revenue_contrib, sessions_contrib,
        primary_kpi_column=client.primary_kpi_column, secondary_kpi_column=client.secondary_kpi_column,
    )

    media_df = media_to_long_df(media, geo_df, time_index)
    controls_kpi_df = controls_df.merge(kpi_df, on=["geo", "time"])

    media_df.to_csv(output_dir / "media.csv", index=False)
    controls_kpi_df.to_csv(output_dir / "controls_kpi.csv", index=False)
    geo_df.to_csv(output_dir / "geo_population.csv", index=False)

    ground_truth = {
        "client_id": client.client_id,
        "config": {
            "seed": cfg.seed, "n_geos": cfg.n_geos, "n_weeks": cfg.n_weeks,
            "start_date": cfg.start_date, "total_annual_media_budget_eur": cfg.total_annual_media_budget_eur,
            "noise_sigma": cfg.noise_sigma, "missing_week_rate": cfg.missing_week_rate,
        },
        "channels": channel_ground_truth,
        "kpi": kpi_ground_truth,
    }
    (ground_truth_dir / f"{client.client_id}_ground_truth.json").write_text(
        json.dumps(ground_truth, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    write_report(output_dir, ground_truth_dir, cfg, channel_ground_truth, media_df, controls_kpi_df, geo_df, client)

    print(f"Client: {client.display_name} ({client.client_id})")
    print(f"Media-Daten: {media_df.shape}, Controls/KPI: {controls_kpi_df.shape}")
    print(f"Geschrieben nach: {output_dir}/ und {ground_truth_dir}/")


if __name__ == "__main__":
    main()
