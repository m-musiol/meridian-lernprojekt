"""Client-Konfiguration: Vivora Sport & Fitness (fiktive DTC-Sportswear-/Fitness-Abo-Marke).

Dient als zweiter Demo-Kunde, um die Generalisierung der Pipeline konkret zu belegen (nicht nur
theoretisch): bewusst andere Geo-Zahl, anderer Kanal-Mix (kein TV/Radio/OOH/Affiliate, dafuer
Influencer/App-Install-Kanaele), andere sekundaere KPI (`app_installs` statt `website_sessions`),
und testet den Reach/Frequency-Auto-Erkennungs-Pfad (`reach_frequency_channels=None`), waehrend
Nordpunkt weiterhin die explizite Deklaration testet.
"""

from client_config import ChannelConfig, ClientConfig, GeneratorSettings

CHANNELS: tuple[ChannelConfig, ...] = (
    ChannelConfig(
        "Paid_Social", 0.25, cost_per_impression=0.007, adstock_decay=0.25,
        hill_ec50_share_of_max_exposure=0.5, hill_slope=1.3,
        target_roi=1.8, target_sessions_per_1000_eur=60,
        has_reach_frequency=True, base_frequency=3.0,
    ),
    ChannelConfig(
        "Paid_Search_Brand", 0.10, cost_per_impression=0.018, adstock_decay=0.10,
        hill_ec50_share_of_max_exposure=0.6, hill_slope=1.0,
        target_roi=3.5, target_sessions_per_1000_eur=80,
    ),
    ChannelConfig(
        "Paid_Search_NonBrand", 0.15, cost_per_impression=0.014, adstock_decay=0.15,
        hill_ec50_share_of_max_exposure=0.6, hill_slope=1.0,
        target_roi=2.2, target_sessions_per_1000_eur=100,
    ),
    ChannelConfig(
        "Programmatic_Display", 0.15, cost_per_impression=0.003, adstock_decay=0.20,
        hill_ec50_share_of_max_exposure=0.5, hill_slope=1.0,
        target_roi=1.1, target_sessions_per_1000_eur=50,
    ),
    ChannelConfig(
        "Video_YouTube", 0.10, cost_per_impression=0.011, adstock_decay=0.30,
        hill_ec50_share_of_max_exposure=0.5, hill_slope=1.2,
        target_roi=1.3, target_sessions_per_1000_eur=35,
    ),
    ChannelConfig(
        "Influencer", 0.15, cost_per_impression=0.009, adstock_decay=0.35,
        hill_ec50_share_of_max_exposure=0.5, hill_slope=1.2,
        target_roi=1.6, target_sessions_per_1000_eur=45,
        has_reach_frequency=True, base_frequency=2.5,
    ),
    ChannelConfig(
        "App_Install_Ads", 0.10, cost_per_impression=0.016, adstock_decay=0.15,
        hill_ec50_share_of_max_exposure=0.5, hill_slope=1.0,
        target_roi=1.4, target_sessions_per_1000_eur=150,
    ),
)

CLIENT = ClientConfig(
    client_id="vivora",
    display_name="Vivora Sport & Fitness",
    industry="DTC Sportswear & Fitness-Abo (D-A-CH)",
    currency="EUR",
    data_source="synthetic",
    primary_kpi_column="revenue_eur",
    secondary_kpi_column="app_installs",
    control_columns=(
        "price_index", "promo_flag", "holiday_flag",
        "temperature_c", "consumer_climate_index", "competitor_spend_proxy_eur",
    ),
    reach_frequency_channels=None,  # bewusst: testet den Auto-Erkennungs-Pfad
    data_dir="data/raw/vivora_synthetic",
    ground_truth_dir="data/ground_truth",
    generator=GeneratorSettings(
        seed=7,
        n_geos=6,
        n_weeks=156,
        start_date="2021-01-04",
        total_annual_media_budget_eur=3_000_000.0,
        total_population=20_000_000.0,
        channels=CHANNELS,
        noise_sigma=0.05,
        missing_week_rate=0.0,  # kein bewusster Noise-Layer noetig, testet nur die Generalisierung
    ),
)
