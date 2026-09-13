"""Konfiguration fuer den synthetischen Nordpunkt-Datengenerator (Datenquelle 2, Stufe 1).

Alle Kanal-Parameter (ROI, Adstock-Decay, Saettigung) sind fuer den Lernzweck plausibel gesetzte
Annahmen, keine echten Marktbenchmarks — siehe docs/stakeholder_briefing.md.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChannelConfig:
    name: str
    annual_budget_share: float  # Anteil am Jahres-Media-Budget
    cost_per_impression: float  # EUR je Impression (Kehrwert des CPM/1000)
    adstock_decay: float  # woechentliche Retention-Rate (0-1), hoeher = laenger nachwirkend
    hill_ec50_share_of_max_exposure: float  # Halbsaettigungspunkt als Anteil vom max. adstockten Exposure
    hill_slope: float  # Steilheit der Saettigungskurve
    target_roi: float  # Ground Truth: Umsatz (EUR) je ausgegebenem Euro
    target_sessions_per_1000_eur: float  # Ground Truth: Website-Sessions je 1.000 EUR Spend
    has_reach_frequency: bool = False
    base_frequency: float = 1.0  # nur relevant, falls has_reach_frequency


DEFAULT_CHANNELS: tuple[ChannelConfig, ...] = (
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


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 42
    n_geos: int = 10
    n_weeks: int = 156
    start_date: str = "2021-01-04"
    total_annual_media_budget_eur: float = 10_000_000.0
    total_population: float = 40_000_000.0
    noise_sigma: float = 0.05  # multiplikative Rauschstaerke (Messfehler)
    missing_week_rate: float = 0.05  # Anteil fehlender Wochen bei OOH/Radio
    channels: tuple[ChannelConfig, ...] = field(default_factory=lambda: DEFAULT_CHANNELS)
