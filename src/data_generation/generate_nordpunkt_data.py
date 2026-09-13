"""Generiert den synthetischen Nordpunkt-Datensatz (Datenquelle 2, Stufe 1).

Erzeugt Media-, Kontroll- und KPI-Daten fuer die fiktive Marke "Nordpunkt Home & Living"
gemaess docs/wissensbasis_pipeline.md Abschnitt 1 und docs/stakeholder_briefing.md.
Alle wahren Effektstaerken (Adstock, Saettigung, ROI, Kontroll-Koeffizienten) werden als
Ground Truth gespeichert, um Modell-Ergebnisse spaeter dagegen zu validieren (Stufe 8).

Deterministisch ueber --seed; alle Stellschrauben (Geo-Zahl, Zeitraum, Rausch-Intensitaet,
fehlende Wochen) sind CLI-Parameter, siehe --help.
"""

import argparse
import json
import pathlib

import numpy as np
import pandas as pd

from config import ChannelConfig, GeneratorConfig
from transforms import apply_adstock, hill_saturation


def make_time_index(cfg: GeneratorConfig) -> pd.DatetimeIndex:
    return pd.date_range(start=cfg.start_date, periods=cfg.n_weeks, freq="W-MON")


def make_geo_population(cfg: GeneratorConfig, rng: np.random.Generator) -> pd.DataFrame:
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
    channel: ChannelConfig, cfg: GeneratorConfig, seasonal: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    annual_budget = cfg.total_annual_media_budget_eur * channel.annual_budget_share
    base_weekly = annual_budget / 52.0
    trend = 1.0 + 0.002 * np.arange(cfg.n_weeks)  # leichtes organisches Wachstum ueber 3 Jahre
    noise = rng.lognormal(mean=0.0, sigma=cfg.noise_sigma, size=cfg.n_weeks)
    return base_weekly * trend * seasonal * noise


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
    cfg: GeneratorConfig,
    seasonal: np.ndarray,
    geo_df: pd.DataFrame,
    rng: np.random.Generator,
) -> np.ndarray:
    """Radio hat einen eigenen Sockel-Spend plus einen TV-korrelierten Anteil (bewusste Kollinearitaet)."""
    own_baseline = split_across_geos(national_spend_series(channel, cfg, seasonal, rng), geo_df, rng)
    correlated_extra = 0.45 * tv_spend_geo * rng.lognormal(mean=0.0, sigma=0.15, size=tv_spend_geo.shape)
    return own_baseline + correlated_extra


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
    cfg: GeneratorConfig, rng: np.random.Generator, geo_df: pd.DataFrame, seasonal: np.ndarray
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
    media: dict, cfg: GeneratorConfig
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


def generate_controls_and_organic(
    cfg: GeneratorConfig,
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
        + 0.01 * np.nan_to_num(media["Paid_Search_Brand"]["impressions"], nan=0.0)
    )
    social_organic_reach = (
        2000 * geo_df["pop_share"].to_numpy().reshape(-1, 1)
        * rng.lognormal(0, 0.2, size=(n_geos, n_weeks))
        + 0.02 * np.nan_to_num(media["Paid_Social"]["impressions"], nan=0.0)
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
    cfg: GeneratorConfig,
    rng: np.random.Generator,
    geo_df: pd.DataFrame,
    controls_df: pd.DataFrame,
    revenue_contrib: dict,
    sessions_contrib: dict,
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
        frames.append(pd.DataFrame({"geo": geo, "time": time_index, "revenue_eur": revenue[i], "website_sessions": sessions[i]}))
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


def write_report(output_dir: pathlib.Path, ground_truth_dir: pathlib.Path, cfg: GeneratorConfig, channel_gt: dict) -> None:
    report_path = pathlib.Path("reports/stufe1_datengenerierung_bericht.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Stufe 1 — Bericht: Synthetischer Nordpunkt-Datensatz (Datenquelle 2)\n",
        f"Seed: `{cfg.seed}` | Geos: {cfg.n_geos} | Wochen: {cfg.n_weeks} | "
        f"Start: {cfg.start_date} | Jahresbudget: {cfg.total_annual_media_budget_eur:,.0f} EUR\n",
        "\n## Ground-Truth-ROI je Kanal (realisiert vs. Ziel)\n",
        "| Kanal | Ziel-ROI | realisiert | Adstock-Decay | Hill-Slope |",
        "|---|---|---|---|---|",
    ]
    for name, gt in channel_gt.items():
        lines.append(
            f"| {name} | {gt['target_roi']:.2f} | {gt['realized_roi']:.2f} | "
            f"{gt['adstock_decay']:.2f} | {gt['hill_slope']:.2f} |"
        )
    lines.append(
        f"\nAusgabe: `{output_dir.as_posix()}/` (media.csv, controls_kpi.csv), "
        f"Ground Truth: `{ground_truth_dir.as_posix()}/`.\n"
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generiert den synthetischen Nordpunkt-Datensatz.")
    parser.add_argument("--seed", type=int, default=GeneratorConfig.seed)
    parser.add_argument("--n-geos", type=int, default=GeneratorConfig.n_geos)
    parser.add_argument("--n-weeks", type=int, default=GeneratorConfig.n_weeks)
    parser.add_argument("--start-date", default=GeneratorConfig.start_date)
    parser.add_argument("--annual-media-budget", type=float, default=GeneratorConfig.total_annual_media_budget_eur)
    parser.add_argument("--noise-sigma", type=float, default=GeneratorConfig.noise_sigma)
    parser.add_argument("--missing-week-rate", type=float, default=GeneratorConfig.missing_week_rate)
    parser.add_argument("--output-dir", default="data/raw/nordpunkt_synthetic")
    parser.add_argument("--ground-truth-dir", default="data/ground_truth")
    args = parser.parse_args()

    cfg = GeneratorConfig(
        seed=args.seed, n_geos=args.n_geos, n_weeks=args.n_weeks, start_date=args.start_date,
        total_annual_media_budget_eur=args.annual_media_budget, noise_sigma=args.noise_sigma,
        missing_week_rate=args.missing_week_rate,
    )
    rng = np.random.default_rng(cfg.seed)
    output_dir = pathlib.Path(args.output_dir)
    ground_truth_dir = pathlib.Path(args.ground_truth_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ground_truth_dir.mkdir(parents=True, exist_ok=True)

    time_index = make_time_index(cfg)
    geo_df = make_geo_population(cfg, rng)
    seasonal = make_seasonal_multiplier(cfg.n_weeks)

    media = build_media_data(cfg, rng, geo_df, seasonal)
    revenue_contrib, sessions_contrib, channel_ground_truth = compute_channel_contributions(media, cfg)
    controls_df = generate_controls_and_organic(cfg, rng, time_index, geo_df, media)
    kpi_df, kpi_ground_truth = generate_kpis(cfg, rng, geo_df, controls_df, revenue_contrib, sessions_contrib)

    media_df = media_to_long_df(media, geo_df, time_index)
    controls_kpi_df = controls_df.merge(kpi_df, on=["geo", "time"])

    media_df.to_csv(output_dir / "media.csv", index=False)
    controls_kpi_df.to_csv(output_dir / "controls_kpi.csv", index=False)
    geo_df.to_csv(output_dir / "geo_population.csv", index=False)

    ground_truth = {
        "config": {
            "seed": cfg.seed, "n_geos": cfg.n_geos, "n_weeks": cfg.n_weeks,
            "start_date": cfg.start_date, "total_annual_media_budget_eur": cfg.total_annual_media_budget_eur,
            "noise_sigma": cfg.noise_sigma, "missing_week_rate": cfg.missing_week_rate,
        },
        "channels": channel_ground_truth,
        "kpi": kpi_ground_truth,
    }
    (ground_truth_dir / "nordpunkt_ground_truth.json").write_text(
        json.dumps(ground_truth, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    write_report(output_dir, ground_truth_dir, cfg, channel_ground_truth)

    print(f"Media-Daten: {media_df.shape}, Controls/KPI: {controls_kpi_df.shape}")
    print(f"Geschrieben nach: {output_dir}/ und {ground_truth_dir}/")


if __name__ == "__main__":
    main()
