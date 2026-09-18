"""Stufe 2 — Datenqualitaets- & Eignungspruefung (Gate 1).

Prueft den Datensatz eines konfigurierten Kunden (`clients/<client_id>/config.py`) anhand der in
docs/wissensbasis_pipeline.md Abschnitt 2 (Stufe 2) festgelegten Kriterien und schreibt eine
Ampel-Bewertung nach reports/stage_gates/<client_id>/stage2_eignungsbericht.md.

Entscheidungslogik: gruen -> weiter zu Stufe 3, gelb -> mit dokumentierten Einschraenkungen
weiter, rot -> zurueck zu Stufe 1 mit Korrekturplan.
"""

import argparse
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # src/ auf den Pfad
from client_config import ClientConfig, load_client_config
from data_quality.checks import (
    CheckResult,
    check_collinearity,
    check_completeness,
    check_controls_availability,
    check_geo_population,
    check_granularity,
    check_outliers_and_units,
    check_reach_frequency,
    check_spend_variance,
    check_time_vs_complexity,
)

AMPEL_EMOJI = {"gruen": "🟢", "gelb": "🟡", "rot": "🔴"}


def load_data(raw_dir: pathlib.Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    media_df = pd.read_csv(raw_dir / "media.csv", parse_dates=["time"])
    controls_kpi_df = pd.read_csv(raw_dir / "controls_kpi.csv", parse_dates=["time"])
    geo_df = pd.read_csv(raw_dir / "geo_population.csv")
    return media_df, controls_kpi_df, geo_df


def run_all_checks(
    media_df: pd.DataFrame, controls_kpi_df: pd.DataFrame, geo_df: pd.DataFrame, client: ClientConfig
) -> list[CheckResult]:
    n_geos = geo_df.shape[0]
    n_weeks = media_df["time"].nunique()
    n_channels = media_df["channel"].nunique()
    kpi_columns = tuple(c for c in (client.primary_kpi_column, client.secondary_kpi_column) if c)
    n_controls = (
        len(client.control_columns) if client.control_columns is not None
        else len([c for c in controls_kpi_df.columns if c not in ("geo", "time", "population", *kpi_columns)])
    )

    return [
        check_completeness(media_df),
        check_granularity(media_df, controls_kpi_df, geo_df),
        check_time_vs_complexity(n_geos, n_weeks, n_channels, n_controls),
        check_spend_variance(media_df),
        check_collinearity(media_df, geo_df),
        check_outliers_and_units(media_df, controls_kpi_df, kpi_columns),
        check_controls_availability(controls_kpi_df, client.control_columns, kpi_columns),
        check_geo_population(geo_df, n_geos),
        check_reach_frequency(media_df, client.reach_frequency_channels),
    ]


def aggregate_verdict(results: list[CheckResult]) -> str:
    statuses = {r.status for r in results}
    if "rot" in statuses:
        return "rot"
    if "gelb" in statuses:
        return "gelb"
    return "gruen"


def write_report(
    results: list[CheckResult], verdict: str, raw_dir: pathlib.Path, output_path: pathlib.Path, client: ClientConfig
) -> None:
    verdict_text = {
        "gruen": "**GRUEN — weiter zu Stufe 3 (EDA).**",
        "gelb": "**GELB — mit dokumentierten Einschraenkungen weiter zu Stufe 3.** "
        "Limitierungen muessen in `docs/model_card.md` vermerkt werden.",
        "rot": "**ROT — zurueck zu Stufe 1.** Konkreter Korrekturplan noetig, bevor Modellierungszeit investiert wird.",
    }
    lines = [
        "# Stufe 2 — Eignungsbericht (Gate 1)\n",
        f"Kunde: **{client.display_name}** ({client.client_id}). Datengrundlage: `{raw_dir.as_posix()}/`.\n",
        f"## Gesamtvotum: {AMPEL_EMOJI[verdict]} {verdict_text[verdict]}\n",
        "## Kriterien im Detail\n",
        "| Ampel | Kriterium | Messwert | Begruendung des Schwellenwerts | Empfehlung |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {AMPEL_EMOJI[r.status]} | {r.name} | {r.summary} | {r.reasoning} | {r.recommendation or '—'} |"
        )

    yellow_or_red = [r for r in results if r.status != "gruen"]
    if yellow_or_red:
        lines.append("\n## Fuer die Model Card zu dokumentierende Limitierungen\n")
        for r in yellow_or_red:
            lines.append(f"- **{r.name}** ({AMPEL_EMOJI[r.status]}): {r.recommendation}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows-Konsole (cp1252) kann Ampel-Emojis sonst nicht ausgeben

    parser = argparse.ArgumentParser(description="Stufe-2-Eignungspruefung fuer einen konfigurierten Kunden.")
    parser.add_argument("--client", default="nordpunkt", help="Client-ID unter clients/<id>/config.py")
    parser.add_argument("--raw-dir", default=None, help="Default: client.data_dir")
    parser.add_argument("--output", default=None, help="Default: reports/stage_gates/<client_id>/stage2_eignungsbericht.md")
    args = parser.parse_args()

    client = load_client_config(args.client)
    raw_dir = pathlib.Path(args.raw_dir or client.data_dir)
    output_path = pathlib.Path(args.output or f"reports/stage_gates/{client.client_id}/stage2_eignungsbericht.md")

    media_df, controls_kpi_df, geo_df = load_data(raw_dir)
    results = run_all_checks(media_df, controls_kpi_df, geo_df, client)
    verdict = aggregate_verdict(results)
    write_report(results, verdict, raw_dir, output_path, client)

    print(f"Kunde: {client.display_name} ({client.client_id})")
    print(f"Gesamtvotum: {AMPEL_EMOJI[verdict]} {verdict}")
    for r in results:
        print(f"  {AMPEL_EMOJI[r.status]} {r.name}: {r.summary}")
    print(f"Bericht geschrieben nach: {output_path}")


if __name__ == "__main__":
    main()
