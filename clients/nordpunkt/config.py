"""Client-Konfiguration: Nordpunkt Home & Living (fiktiver D-A-CH-Moebel-/Wohnaccessoires-Retailer).

Eins-zu-eins-Extraktion der bisherigen Hardcode-Werte aus `src/data_generation/config.py` und
`src/data_quality/checks.py`/`run_stage2_check.py` — siehe docs/stakeholder_briefing.md fuer die
fachliche Begruendung der Annahmen.
"""

from client_config import ChannelConfig, ClientConfig, GeneratorSettings

CHANNELS: tuple[ChannelConfig, ...] = (
    ChannelConfig(
        "TV", 0.30, cost_per_impression=0.008, adstock_decay=0.60,
        hill_ec50_share_of_max_exposure=0.5, hill_slope=1.5,
        target_roi=1.5, target_sessions_per_1000_eur=5,
        has_reach_frequency=True, base_frequency=4.0,
    ),
    ChannelConfig(
        "Video_YouTube", 0.05, cost_per_impression=0.012, adstock_decay=0.30,
        hill_ec50_share_of_max_exposure=0.5, hill_slope=1.2,
        target_roi=1.4, target_sessions_per_1000_eur=40,
    ),
    ChannelConfig(
        "Programmatic_Display", 0.15, cost_per_impression=0.003, adstock_decay=0.20,
        hill_ec50_share_of_max_exposure=0.5, hill_slope=1.0,
        target_roi=1.2, target_sessions_per_1000_eur=60,
    ),
    ChannelConfig(
        "Paid_Social", 0.15, cost_per_impression=0.006, adstock_decay=0.25,
        hill_ec50_share_of_max_exposure=0.5, hill_slope=1.3,
        target_roi=2.0, target_sessions_per_1000_eur=70,
        has_reach_frequency=True, base_frequency=3.0,
    ),
    ChannelConfig(
        "Paid_Search_Brand", 0.08, cost_per_impression=0.020, adstock_decay=0.10,
        hill_ec50_share_of_max_exposure=0.6, hill_slope=1.0,
        target_roi=4.0, target_sessions_per_1000_eur=90,
    ),
    ChannelConfig(
        "Paid_Search_NonBrand", 0.12, cost_per_impression=0.015, adstock_decay=0.15,
        hill_ec50_share_of_max_exposure=0.6, hill_slope=1.0,
        target_roi=2.5, target_sessions_per_1000_eur=110,
    ),
    ChannelConfig(
        "Affiliate", 0.05, cost_per_impression=0.010, adstock_decay=0.20,
        hill_ec50_share_of_max_exposure=0.5, hill_slope=1.0,
        target_roi=2.0, target_sessions_per_1000_eur=50,
    ),
    ChannelConfig(
        "Out_of_Home", 0.05, cost_per_impression=0.004, adstock_decay=0.40,
        hill_ec50_share_of_max_exposure=0.5, hill_slope=1.2,
        target_roi=1.0, target_sessions_per_1000_eur=3,
    ),
    ChannelConfig(
        "Radio", 0.05, cost_per_impression=0.005, adstock_decay=0.50,
        hill_ec50_share_of_max_exposure=0.5, hill_slope=1.2,
        target_roi=1.1, target_sessions_per_1000_eur=4,
    ),
)

CLIENT = ClientConfig(
    client_id="nordpunkt",
    display_name="Nordpunkt Home & Living",
    industry="Moebel & Wohnaccessoires (D-A-CH)",
    currency="EUR",
    data_source="synthetic",
    primary_kpi_column="revenue_eur",
    secondary_kpi_column="website_sessions",
    control_columns=(
        "price_index", "promo_flag", "holiday_flag",
        "temperature_c", "consumer_climate_index", "competitor_spend_proxy_eur",
    ),
    reach_frequency_channels=("TV", "Paid_Social"),
    data_dir="data/raw/nordpunkt_synthetic",
    ground_truth_dir="data/ground_truth",
    generator=GeneratorSettings(
        seed=42,
        n_geos=10,
        n_weeks=156,
        start_date="2021-01-04",
        total_annual_media_budget_eur=10_000_000.0,
        total_population=40_000_000.0,
        channels=CHANNELS,
        noise_sigma=0.05,
        missing_week_rate=0.05,
    ),
)
