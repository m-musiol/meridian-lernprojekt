"""Geteilte Plotly-Chart-Bausteine fuer Stufe 3 (EDA) und die Streamlit-App.

Sechs Charts, bewusst kein Kartenmaterial (synthetische Geos haben keine echten Geoformen) und
keine volle STL-Saisonzerlegung (kein statsmodels-Bedarf fuer dieses Lernprojekt). Nutzt dieselbe
Pro-Kopf-Geo-Wochen-Normalisierung wie Stufe 2 (`data_quality.geo_normalization`), damit Gate-1-
Zahlen und EDA-Heatmap garantiert konsistent sind.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/ auf den Pfad
from data_quality.geo_normalization import geo_week_spend_per_capita_matrix

_PALETTE = px.colors.qualitative.Safe


def channel_color_map(channel_names: list[str]) -> dict[str, str]:
    """Feste Kanal-Farbzuordnung, damit Farben ueber alle Charts/Tabs konsistent bleiben."""
    ordered = sorted(channel_names)
    return {name: _PALETTE[i % len(_PALETTE)] for i, name in enumerate(ordered)}


def _national_weekly(df: pd.DataFrame, value_col: str, group_col: str | None = None) -> pd.DataFrame:
    keys = ["time"] if group_col is None else ["time", group_col]
    return df.groupby(keys, as_index=False)[value_col].sum()


def plot_kpi_trend(controls_kpi_df: pd.DataFrame, primary_kpi: str, secondary_kpi: str | None) -> go.Figure:
    """KPI-Trend ueber Zeit (nationale Summe je Woche), primaer/sekundaer als zwei Subplots.

    Bewusst zwei uebereinanderliegende Ein-Achsen-Plots statt einem einzigen Chart mit zwei
    y-Achsen unterschiedlicher Skala (Dual-Achsen-Charts suggerieren leicht einen Zusammenhang,
    der nur durch die willkuerliche Achsenskalierung entsteht — anerkanntes Anti-Pattern).
    """
    rows = 2 if secondary_kpi else 1
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.12,
                         subplot_titles=[primary_kpi] + ([secondary_kpi] if secondary_kpi else []))
    primary = _national_weekly(controls_kpi_df, primary_kpi)
    fig.add_trace(go.Scatter(x=primary["time"], y=primary[primary_kpi], mode="lines", name=primary_kpi), row=1, col=1)
    if secondary_kpi:
        secondary = _national_weekly(controls_kpi_df, secondary_kpi)
        fig.add_trace(
            go.Scatter(x=secondary["time"], y=secondary[secondary_kpi], mode="lines", name=secondary_kpi),
            row=2, col=1,
        )
    fig.update_layout(title="KPI-Trend ueber Zeit (national, woechentlich)", showlegend=False, height=500)
    return fig


def plot_channel_spend_share(media_df: pd.DataFrame) -> go.Figure:
    """Gestapelter 100%-Bar-Chart der Spend-Anteile je Kanal und Quartal (zeigt Mix-Verschiebungen)."""
    df = media_df.copy()
    df["quarter"] = pd.to_datetime(df["time"]).dt.to_period("Q").astype(str)
    by_quarter = df.groupby(["quarter", "channel"], as_index=False)["spend_eur"].sum()
    totals = by_quarter.groupby("quarter")["spend_eur"].transform("sum")
    by_quarter["share"] = by_quarter["spend_eur"] / totals

    colors = channel_color_map(sorted(media_df["channel"].unique()))
    fig = go.Figure()
    for channel in sorted(by_quarter["channel"].unique()):
        sub = by_quarter[by_quarter["channel"] == channel]
        fig.add_trace(go.Bar(x=sub["quarter"], y=sub["share"], name=channel, marker_color=colors[channel]))
    fig.update_layout(
        barmode="stack", title="Spend-Share nach Kanal (je Quartal)",
        yaxis=dict(tickformat=".0%", title="Anteil am Quartals-Spend"), xaxis_title="Quartal",
    )
    return fig


def plot_spend_vs_kpi_indexed(media_df: pd.DataFrame, controls_kpi_df: pd.DataFrame, primary_kpi: str) -> go.Figure:
    """Gesamt-Spend vs. primaere KPI, beide auf 100 zur ersten Woche indexiert, eine Achse."""
    spend = _national_weekly(media_df, "spend_eur").sort_values("time")
    kpi = _national_weekly(controls_kpi_df, primary_kpi).sort_values("time")
    spend_indexed = 100 * spend["spend_eur"] / spend["spend_eur"].iloc[0]
    kpi_indexed = 100 * kpi[primary_kpi] / kpi[primary_kpi].iloc[0]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=spend["time"], y=spend_indexed, mode="lines", name="Gesamt-Spend (indexiert)"))
    fig.add_trace(go.Scatter(x=kpi["time"], y=kpi_indexed, mode="lines", name=f"{primary_kpi} (indexiert)"))
    fig.update_layout(
        title="Spend vs. KPI (beide auf 100 = erste Woche indexiert)",
        yaxis_title="Index (Woche 1 = 100)", xaxis_title="Woche",
    )
    return fig


def plot_seasonality(controls_kpi_df: pd.DataFrame, primary_kpi: str) -> go.Figure:
    """KPI je Kalenderwoche, Jahre uebereinandergelegt — zeigt wiederkehrende Saisonmuster."""
    df = _national_weekly(controls_kpi_df, primary_kpi).copy()
    df["time"] = pd.to_datetime(df["time"])
    df["year"] = df["time"].dt.isocalendar().year
    df["week_of_year"] = df["time"].dt.isocalendar().week

    fig = go.Figure()
    for year in sorted(df["year"].unique()):
        sub = df[df["year"] == year]
        fig.add_trace(go.Scatter(x=sub["week_of_year"], y=sub[primary_kpi], mode="lines", name=str(year)))
    fig.update_layout(
        title=f"Saisonalitaet: {primary_kpi} je Kalenderwoche (Jahre uebereinandergelegt)",
        xaxis_title="Kalenderwoche", yaxis_title=primary_kpi,
    )
    return fig


def plot_channel_correlation_heatmap(media_df: pd.DataFrame, geo_df: pd.DataFrame) -> go.Figure:
    """Kanal-Korrelations-Heatmap — identische Berechnung wie der Stufe-2-Kollinearitaets-Check."""
    matrix = geo_week_spend_per_capita_matrix(media_df, geo_df)
    corr = matrix.corr()
    fig = px.imshow(
        corr, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, text_auto=".2f",
        title="Kanal-Spend-Korrelation (pro Kopf, Geo-Wochen-Ebene)",
    )
    return fig


def plot_geo_variation(controls_kpi_df: pd.DataFrame, geo_df: pd.DataFrame, primary_kpi: str) -> go.Figure:
    """Sortierter Bar-Chart: durchschnittliche KPI pro Kopf je Geo (keine Karte, da synthetisch)."""
    # controls_kpi_df kann bereits eine eigene "population"-Spalte haben (z.B. Generator-Output) —
    # geo_df ist hier die verbindliche Quelle, daher vor dem Merge entfernen (sonst population_x/_y).
    base = controls_kpi_df.drop(columns=["population"], errors="ignore")
    merged = base.merge(geo_df[["geo", "population"]], on="geo")
    merged["kpi_per_capita"] = merged[primary_kpi] / merged["population"]
    by_geo = merged.groupby("geo", as_index=False)["kpi_per_capita"].mean().sort_values("kpi_per_capita")

    fig = go.Figure(go.Bar(x=by_geo["kpi_per_capita"], y=by_geo["geo"], orientation="h"))
    fig.update_layout(
        title=f"Geo-Level-Variation: {primary_kpi} pro Kopf (Durchschnitt ueber die Zeit)",
        xaxis_title=f"{primary_kpi} pro Kopf", yaxis_title="Geo",
    )
    return fig
