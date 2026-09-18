"""Client-Konfiguration: macht die Pipeline fuer beliebige Kunden einsetzbar statt nur Nordpunkt.

Zwei Betriebsarten pro Kunde (`ClientConfig.data_source`):
- "synthetic": Daten werden von `src/data_generation/generate_synthetic_data.py` erzeugt, `generator`
  ist Pflicht (enthaelt alle Ground-Truth-Parameter: Adstock, Hill-Saettigung, ROI je Kanal).
- "uploaded": Daten kommen von aussen (z.B. Streamlit-Upload) und muessen dem Unified Input Schema
  entsprechen (docs/unified_input_schema.md); `generator` ist None, da echte Ground Truth unbekannt ist.

`control_columns`/`reach_frequency_channels` = None bedeutet "aus den tatsaechlichen Daten ableiten"
(siehe `src/data_quality/checks.py`) — noetig, damit hochgeladene Kunden keine zusaetzlichen
Metadaten deklarieren muessen, nur die CSV-Struktur einhalten.

Neue Kunden anlegen: eigenes Modul unter `clients/<client_id>/config.py` mit einer `CLIENT`-Konstante
vom Typ `ClientConfig` (siehe `clients/nordpunkt/config.py` als Vorlage).
"""

from __future__ import annotations

import importlib.util
import pathlib
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ChannelConfig:
    name: str
    annual_budget_share: float  # Anteil am Jahres-Media-Budget
    cost_per_impression: float  # EUR je Impression (Kehrwert des CPM/1000)
    adstock_decay: float  # woechentliche Retention-Rate (0-1), hoeher = laenger nachwirkend
    hill_ec50_share_of_max_exposure: float  # Halbsaettigungspunkt als Anteil vom max. adstockten Exposure
    hill_slope: float  # Steilheit der Saettigungskurve
    target_roi: float  # Ground Truth: Umsatz (EUR) je ausgegebenem Euro
    target_sessions_per_1000_eur: float  # Ground Truth: sekundaere KPI je 1.000 EUR Spend
    has_reach_frequency: bool = False
    base_frequency: float = 1.0  # nur relevant, falls has_reach_frequency


@dataclass(frozen=True)
class GeneratorSettings:
    """Nur relevant, wenn ClientConfig.data_source == "synthetic"."""

    seed: int
    n_geos: int
    n_weeks: int
    start_date: str
    total_annual_media_budget_eur: float
    total_population: float
    channels: tuple[ChannelConfig, ...]
    noise_sigma: float = 0.05
    missing_week_rate: float = 0.05


@dataclass(frozen=True)
class ClientConfig:
    client_id: str
    display_name: str
    industry: str
    currency: str = "EUR"
    data_source: Literal["synthetic", "uploaded"] = "synthetic"
    primary_kpi_column: str = "revenue_eur"
    secondary_kpi_column: str | None = "website_sessions"
    control_columns: tuple[str, ...] | None = None  # None => aus Daten ableiten
    reach_frequency_channels: tuple[str, ...] | None = None  # None => aus Daten ableiten
    data_dir: str = "data/raw/nordpunkt_synthetic"
    ground_truth_dir: str | None = "data/ground_truth"
    generator: GeneratorSettings | None = field(default=None)

    def __post_init__(self) -> None:
        if self.data_source == "synthetic" and self.generator is None:
            raise ValueError(f"Client '{self.client_id}': data_source='synthetic' braucht 'generator'.")


CLIENTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "clients"


def load_client_config(client_id: str) -> ClientConfig:
    """Laedt `clients/<client_id>/config.py` und gibt dessen `CLIENT`-Konstante zurueck."""
    client_dir = CLIENTS_DIR / client_id
    config_path = client_dir / "config.py"
    if not config_path.exists():
        available = sorted(p.name for p in CLIENTS_DIR.iterdir() if p.is_dir()) if CLIENTS_DIR.exists() else []
        raise FileNotFoundError(
            f"Keine Konfiguration fuer Client '{client_id}' gefunden ({config_path}). "
            f"Verfuegbare Clients: {available}"
        )
    spec = importlib.util.spec_from_file_location(f"clients.{client_id}.config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client: ClientConfig = module.CLIENT
    if client.client_id != client_id:
        raise ValueError(
            f"clients/{client_id}/config.py: CLIENT.client_id ist '{client.client_id}', erwartet '{client_id}'."
        )
    return client
