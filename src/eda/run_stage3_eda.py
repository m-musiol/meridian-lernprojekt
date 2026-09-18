"""Stufe 3 — Explorative Datenanalyse (EDA).

Erzeugt sechs interaktive Plotly-Charts (siehe `src/visualization/charts.py`) fuer einen
konfigurierten Kunden und schreibt sie als eigenstaendige HTML-Dateien nach
`reports/eda/<client_id>/`, zusammen mit einem erklaerenden `eda_bericht.md`.

Nutzt bevorzugt die bereinigte Media-Datei aus Stufe 4 (`data/interim/<client_id>/media_clean.csv`,
siehe `src/features/handle_missing_media_weeks.py`), falls vorhanden — sonst die Rohdaten mit
einer Warnung (fehlende Wochen wuerden dann als Luecken im Chart erscheinen).
"""

import argparse
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # src/ auf den Pfad
from client_config import ClientConfig, load_client_config
from visualization.charts import (
    plot_channel_correlation_heatmap,
    plot_channel_spend_share,
    plot_geo_variation,
    plot_kpi_trend,
    plot_seasonality,
    plot_spend_vs_kpi_indexed,
)

CHARTS = (
    ("kpi_trend", "KPI-Trend ueber Zeit", "Zeigt Wachstum, Rueckgaenge und grobe Saisonmuster der "
     "Zielgroessen auf einen Blick — der erste Chart, den ein Stakeholder normalerweise sehen will."),
    ("spend_share", "Spend-Share nach Kanal", "Zeigt, wie sich der Media-Mix ueber die Zeit verschiebt "
     "(z.B. saisonale Umschichtungen) — Balken statt eines einzelnen Kreisdiagramms, weil sich der "
     "Mix ueber ein Jahr veraendert, nicht statisch ist."),
    ("spend_vs_kpi", "Spend vs. KPI (indexiert)", "Beide Linien auf 100 = erste Woche indexiert und auf "
     "einer Achse dargestellt (bewusst kein Dual-Achsen-Chart, der durch willkuerliche Skalierung "
     "einen Zusammenhang vortaeuschen koennte). Zeigt nur grobe Ko-Bewegung — keine kausale Aussage, "
     "dafuer ist Stufe 5-8 (das eigentliche Modell) da."),
    ("seasonality", "Saisonalitaet", "Kalenderwochen der einzelnen Jahre uebereinandergelegt — zeigt, "
     "ob sich wiederkehrende Muster (z.B. Q4-Peak) Jahr fuer Jahr aehnlich zeigen."),
    ("correlation_heatmap", "Kanal-Korrelations-Heatmap", "Identische Berechnung wie der Stufe-2-"
     "Kollinearitaets-Check (pro Kopf, Geo-Wochen-Ebene) — visualisiert, welche Kanalpaare sich "
     "schwer trennen lassen werden."),
    ("geo_variation", "Geo-Level-Variation", "Durchschnittliche KPI pro Kopf je Geo, sortiert. Keine "
     "Kartendarstellung: die synthetischen Geos (`Region_01` ...) haben keine echten Geoformen, eine "
     "Karte waere hier nur Dekoration."),
)


def load_media_data(client: ClientConfig) -> tuple[pd.DataFrame, bool]:
    """Bevorzugt die bereinigte Stufe-4-Datei; faellt sonst auf Rohdaten zurueck (mit Warnung)."""
    clean_path = pathlib.Path(f"data/interim/{client.client_id}/media_clean.csv")
    if clean_path.exists():
        return pd.read_csv(clean_path, parse_dates=["time"]), True
    print(f"Warnung: {clean_path} nicht gefunden — nutze Rohdaten (fehlende Wochen bleiben als Luecken sichtbar).")
    return pd.read_csv(pathlib.Path(client.data_dir) / "media.csv", parse_dates=["time"]), False


def write_report(output_dir: pathlib.Path, client: ClientConfig, used_clean_data: bool) -> None:
    lines = [
        f"# Stufe 3 — EDA-Bericht ({client.display_name})\n",
        f"Datenbasis: {'bereinigte Stufe-4-Daten (`media_clean.csv`)' if used_clean_data else 'Rohdaten (Stufe 4 noch nicht gelaufen)'}.\n",
        "Alle Charts sind interaktiv (Hover fuer Werte, Zoom, Legende an-/abschaltbar) — als "
        "eigenstaendige HTML-Dateien in diesem Ordner, keine Bilddateien.\n",
    ]
    for filename, title, explanation in CHARTS:
        lines.append(f"## {title}\n")
        lines.append(f"[`{filename}.html`]({filename}.html)\n")
        lines.append(f"{explanation}\n")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "eda_bericht.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows-Konsole (cp1252) sonst Probleme mit Sonderzeichen

    parser = argparse.ArgumentParser(description="Stufe 3 (EDA): erzeugt Charts fuer einen konfigurierten Kunden.")
    parser.add_argument("--client", default="nordpunkt", help="Client-ID unter clients/<id>/config.py")
    parser.add_argument("--output-dir", default=None, help="Default: reports/eda/<client_id>")
    args = parser.parse_args()

    client = load_client_config(args.client)
    output_dir = pathlib.Path(args.output_dir or f"reports/eda/{client.client_id}")

    media_df, used_clean_data = load_media_data(client)
    controls_kpi_df = pd.read_csv(pathlib.Path(client.data_dir) / "controls_kpi.csv", parse_dates=["time"])
    geo_df = pd.read_csv(pathlib.Path(client.data_dir) / "geo_population.csv")

    figures = {
        "kpi_trend": plot_kpi_trend(controls_kpi_df, client.primary_kpi_column, client.secondary_kpi_column),
        "spend_share": plot_channel_spend_share(media_df),
        "spend_vs_kpi": plot_spend_vs_kpi_indexed(media_df, controls_kpi_df, client.primary_kpi_column),
        "seasonality": plot_seasonality(controls_kpi_df, client.primary_kpi_column),
        "correlation_heatmap": plot_channel_correlation_heatmap(media_df, geo_df),
        "geo_variation": plot_geo_variation(controls_kpi_df, geo_df, client.primary_kpi_column),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, fig in figures.items():
        fig.write_html(output_dir / f"{name}.html", include_plotlyjs="cdn")

    write_report(output_dir, client, used_clean_data)

    print(f"Kunde: {client.display_name} ({client.client_id})")
    print(f"{len(figures)} Charts geschrieben nach: {output_dir}/")


if __name__ == "__main__":
    main()
