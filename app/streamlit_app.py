"""Streamlit-Dashboard: Demo-Kunde waehlen oder eigene Daten hochladen, Stufe 2 (Ampel) und

Stufe 3 (EDA-Charts) interaktiv ansehen. Wiederverwendet ausschliesslich bestehende
Pipeline-Module (`data_quality.checks`, `visualization.charts`) — keine eigene Logik.

Lokal starten: streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import pathlib
import sys

import pandas as pd
import streamlit as st

SRC_DIR = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from client_config import ClientConfig, load_client_config  # noqa: E402
from data_quality.run_stage2_check import AMPEL_EMOJI, aggregate_verdict, run_all_checks  # noqa: E402
from visualization.charts import (  # noqa: E402
    plot_channel_correlation_heatmap,
    plot_channel_spend_share,
    plot_geo_variation,
    plot_kpi_trend,
    plot_seasonality,
    plot_spend_vs_kpi_indexed,
)

CLIENTS_DIR = pathlib.Path(__file__).resolve().parents[1] / "clients"
TEMPLATES_DIR = pathlib.Path(__file__).resolve().parent / "templates"
REQUIRED_MEDIA_COLUMNS = ("geo", "time", "channel", "spend_eur", "impressions")
REQUIRED_GEO_COLUMNS = ("geo", "population")

st.set_page_config(page_title="Meridian MMM — Multi-Client Dashboard", layout="wide")


def list_demo_clients() -> list[str]:
    if not CLIENTS_DIR.exists():
        return []
    return sorted(p.name for p in CLIENTS_DIR.iterdir() if (p / "config.py").exists())


def load_demo_client_data(client: ClientConfig) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Immer die Rohdaten — Stufe 2 (Gate 1) bewertet per Definition die Rohdaten, bevor ueberhaupt

    ueber eine Bereinigung (Stufe 4) entschieden wird. Fuer Stufe 3 (EDA) siehe `load_eda_media_data`.
    """
    data_dir = pathlib.Path(client.data_dir)
    media_df = pd.read_csv(data_dir / "media.csv", parse_dates=["time"])
    controls_kpi_df = pd.read_csv(data_dir / "controls_kpi.csv", parse_dates=["time"])
    geo_df = pd.read_csv(data_dir / "geo_population.csv")
    return media_df, controls_kpi_df, geo_df


def load_eda_media_data(client: ClientConfig, raw_media_df: pd.DataFrame) -> pd.DataFrame:
    """Bevorzugt die bereinigte Stufe-4-Media-Datei fuer Stufe 3, falls vorhanden (wie run_stage3_eda.py)."""
    if client.client_id == "uploaded":
        return raw_media_df
    clean_path = pathlib.Path(f"data/interim/{client.client_id}/media_clean.csv")
    if clean_path.exists():
        return pd.read_csv(clean_path, parse_dates=["time"])
    return raw_media_df


def _validate_upload(media_df: pd.DataFrame, controls_kpi_df: pd.DataFrame, geo_df: pd.DataFrame) -> list[str]:
    errors = []
    missing_media = [c for c in REQUIRED_MEDIA_COLUMNS if c not in media_df.columns]
    if missing_media:
        errors.append(f"media.csv: fehlende Pflichtspalten {missing_media}")
    missing_geo = [c for c in REQUIRED_GEO_COLUMNS if c not in geo_df.columns]
    if missing_geo:
        errors.append(f"geo_population.csv: fehlende Pflichtspalten {missing_geo}")
    if "geo" not in controls_kpi_df.columns or "time" not in controls_kpi_df.columns:
        errors.append("controls_kpi.csv: Spalten 'geo' und 'time' sind Pflicht")
    return errors


def _render_upload_templates() -> None:
    st.sidebar.markdown("**Vorlagen (Unified Input Schema):**")
    for filename in ("media_template.csv", "controls_kpi_template.csv", "geo_population_template.csv"):
        path = TEMPLATES_DIR / filename
        st.sidebar.download_button(f"⬇ {filename}", path.read_bytes(), file_name=filename, key=f"dl_{filename}")


def _handle_upload() -> tuple | None:
    _render_upload_templates()
    media_file = st.sidebar.file_uploader("media.csv", type="csv")
    controls_file = st.sidebar.file_uploader("controls_kpi.csv", type="csv")
    geo_file = st.sidebar.file_uploader("geo_population.csv", type="csv")
    if not (media_file and controls_file and geo_file):
        st.sidebar.info("Bitte alle drei Dateien hochladen (siehe docs/unified_input_schema.md).")
        return None

    media_df = pd.read_csv(media_file, parse_dates=["time"])
    controls_kpi_df = pd.read_csv(controls_file, parse_dates=["time"])
    geo_df = pd.read_csv(geo_file)

    errors = _validate_upload(media_df, controls_kpi_df, geo_df)
    if errors:
        for e in errors:
            st.sidebar.error(e)
        return None
    st.sidebar.success("Alle drei Dateien erfolgreich validiert.")

    kpi_candidates = [c for c in controls_kpi_df.columns if c not in ("geo", "time", "population")]
    if not kpi_candidates:
        st.sidebar.error("controls_kpi.csv braucht mind. eine KPI-Spalte ausser geo/time/population.")
        return None
    primary_kpi = st.sidebar.selectbox("Primaere KPI-Spalte", kpi_candidates)
    secondary_options = ["(keine)"] + [c for c in kpi_candidates if c != primary_kpi]
    secondary_choice = st.sidebar.selectbox("Sekundaere KPI-Spalte (optional)", secondary_options)
    secondary_kpi = None if secondary_choice == "(keine)" else secondary_choice

    client = ClientConfig(
        client_id="uploaded", display_name="Hochgeladener Kunde", industry="unbekannt",
        data_source="uploaded", primary_kpi_column=primary_kpi, secondary_kpi_column=secondary_kpi,
        control_columns=None, reach_frequency_channels=None,
        data_dir="(upload)", ground_truth_dir=None, generator=None,
    )
    return client, media_df, controls_kpi_df, geo_df


def sidebar_client_selection() -> tuple | None:
    st.sidebar.header("Kunde")
    mode = st.sidebar.radio("Datenquelle", ["Demo-Kunde", "Eigene Daten hochladen"])

    if mode == "Demo-Kunde":
        demo_clients = list_demo_clients()
        if not demo_clients:
            st.sidebar.error("Keine Demo-Kunden unter clients/ gefunden.")
            return None
        client_id = st.sidebar.selectbox("Kunde", demo_clients)
        client = load_client_config(client_id)
        media_df, controls_kpi_df, geo_df = load_demo_client_data(client)
        return client, media_df, controls_kpi_df, geo_df

    return _handle_upload()


def render_overview_tab(media_df: pd.DataFrame, controls_kpi_df: pd.DataFrame, geo_df: pd.DataFrame) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Geos", geo_df["geo"].nunique())
    col2.metric("Kanaele", media_df["channel"].nunique())
    col3.metric("Wochen", media_df["time"].nunique())
    st.subheader("media.csv (Ausschnitt)")
    st.dataframe(media_df.head(20))
    st.subheader("controls_kpi.csv (Ausschnitt)")
    st.dataframe(controls_kpi_df.head(20))


def render_stage2_tab(client: ClientConfig, media_df: pd.DataFrame, controls_kpi_df: pd.DataFrame, geo_df: pd.DataFrame) -> None:
    results = run_all_checks(media_df, controls_kpi_df, geo_df, client)
    verdict = aggregate_verdict(results)
    st.subheader(f"Gesamtvotum: {AMPEL_EMOJI[verdict]} {verdict.upper()}")
    for r in results:
        with st.expander(f"{AMPEL_EMOJI[r.status]} {r.name}"):
            st.write(f"**Messwert:** {r.summary}")
            st.write(f"**Begruendung:** {r.reasoning}")
            if r.recommendation:
                st.write(f"**Empfehlung:** {r.recommendation}")


def render_stage3_tab(client: ClientConfig, media_df: pd.DataFrame, controls_kpi_df: pd.DataFrame, geo_df: pd.DataFrame) -> None:
    if client.client_id != "uploaded" and pathlib.Path(f"data/interim/{client.client_id}/media_clean.csv").exists():
        st.caption("Nutzt die bereinigte Stufe-4-Media-Datei (fehlende Wochen interpoliert).")
    st.plotly_chart(
        plot_kpi_trend(controls_kpi_df, client.primary_kpi_column, client.secondary_kpi_column),
        use_container_width=True,
    )
    st.plotly_chart(plot_channel_spend_share(media_df), use_container_width=True)
    st.plotly_chart(
        plot_spend_vs_kpi_indexed(media_df, controls_kpi_df, client.primary_kpi_column),
        use_container_width=True,
    )
    st.plotly_chart(plot_seasonality(controls_kpi_df, client.primary_kpi_column), use_container_width=True)
    st.plotly_chart(plot_channel_correlation_heatmap(media_df, geo_df), use_container_width=True)
    st.plotly_chart(plot_geo_variation(controls_kpi_df, geo_df, client.primary_kpi_column), use_container_width=True)


def main() -> None:
    st.title("Meridian MMM — Multi-Client Dashboard")
    st.caption("Lernprojekt: Marketing-Mix-Modeling-Pipeline fuer Demo-Kunden oder eigene Daten.")

    selection = sidebar_client_selection()
    if selection is None:
        st.info("Waehle links einen Demo-Kunden oder lade eigene Daten hoch.")
        return
    client, media_df, controls_kpi_df, geo_df = selection
    eda_media_df = load_eda_media_data(client, media_df)

    st.subheader(client.display_name)
    tab1, tab2, tab3 = st.tabs(["Datenuebersicht", "Stufe 2 — Eignungspruefung", "Stufe 3 — EDA"])
    with tab1:
        render_overview_tab(media_df, controls_kpi_df, geo_df)
    with tab2:
        render_stage2_tab(client, media_df, controls_kpi_df, geo_df)
    with tab3:
        render_stage3_tab(client, eda_media_df, controls_kpi_df, geo_df)


if __name__ == "__main__":
    main()
