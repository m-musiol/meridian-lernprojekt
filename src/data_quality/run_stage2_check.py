"""Stufe 2 — Datenqualitaets- & Eignungspruefung (Gate 1).

Prueft den synthetischen Nordpunkt-Datensatz (Datenquelle 2) anhand der in
docs/wissensbasis_pipeline.md Abschnitt 2 (Stufe 2) festgelegten Kriterien und schreibt
eine Ampel-Bewertung nach reports/stage_gates/stage2_eignungsbericht.md.

Entscheidungslogik: gruen -> weiter zu Stufe 3, gelb -> mit dokumentierten Einschraenkungen
weiter, rot -> zurueck zu Stufe 1 mit Korrekturplan.
"""

import argparse
import pathlib
import sys

import pandas as pd

from checks import (
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

EXPECTED_RF_CHANNELS = ("TV", "Paid_Social")  # muss zu has_reach_frequency in data_generation/config.py passen
AMPEL_EMOJI = {"gruen": "🟢", "gelb": "🟡", "rot": "🔴"}


def load_data(raw_dir: pathlib.Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    media_df = pd.read_csv(raw_dir / "media.csv", parse_dates=["time"])
    controls_kpi_df = pd.read_csv(raw_dir / "controls_kpi.csv", parse_dates=["time"])
    geo_df = pd.read_csv(raw_dir / "geo_population.csv")
    return media_df, controls_kpi_df, geo_df


def run_all_checks(media_df: pd.DataFrame, controls_kpi_df: pd.DataFrame, geo_df: pd.DataFrame) -> list[CheckResult]:
    n_geos = geo_df.shape[0]
    n_weeks = media_df["time"].nunique()
    n_channels = media_df["channel"].nunique()
    n_controls = 6  # siehe checks.EXPECTED_CONTROLS

    return [
        check_completeness(media_df),
        check_granularity(media_df, controls_kpi_df, geo_df),
        check_time_vs_complexity(n_geos, n_weeks, n_channels, n_controls),
        check_spend_variance(media_df),
        check_collinearity(media_df, geo_df),
        check_outliers_and_units(media_df, controls_kpi_df),
        check_controls_availability(controls_kpi_df),
        check_geo_population(geo_df, n_geos),
        check_reach_frequency(media_df, EXPECTED_RF_CHANNELS),
    ]


def aggregate_verdict(results: list[CheckResult]) -> str:
    statuses = {r.status for r in results}
    if "rot" in statuses:
        return "rot"
    if "gelb" in statuses:
        return "gelb"
    return "gruen"


def write_report(results: list[CheckResult], verdict: str, raw_dir: pathlib.Path, output_path: pathlib.Path) -> None:
    verdict_text = {
        "gruen": "**GRUEN — weiter zu Stufe 3 (EDA).**",
        "gelb": "**GELB — mit dokumentierten Einschraenkungen weiter zu Stufe 3.** "
        "Limitierungen muessen in `docs/model_card.md` vermerkt werden.",
        "rot": "**ROT — zurueck zu Stufe 1.** Konkreter Korrekturplan noetig, bevor Modellierungszeit investiert wird.",
    }
    lines = [
        "# Stufe 2 — Eignungsbericht (Gate 1)\n",
        f"Datengrundlage: `{raw_dir.as_posix()}/` (Nordpunkt-Synthetikdaten, Datenquelle 2).\n",
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

    parser = argparse.ArgumentParser(description="Stufe-2-Eignungspruefung fuer den Nordpunkt-Datensatz.")
    parser.add_argument("--raw-dir", default="data/raw/nordpunkt_synthetic")
    parser.add_argument("--output", default="reports/stage_gates/stage2_eignungsbericht.md")
    args = parser.parse_args()

    raw_dir = pathlib.Path(args.raw_dir)
    output_path = pathlib.Path(args.output)

    media_df, controls_kpi_df, geo_df = load_data(raw_dir)
    results = run_all_checks(media_df, controls_kpi_df, geo_df)
    verdict = aggregate_verdict(results)
    write_report(results, verdict, raw_dir, output_path)

    print(f"Gesamtvotum: {AMPEL_EMOJI[verdict]} {verdict}")
    for r in results:
        print(f"  {AMPEL_EMOJI[r.status]} {r.name}: {r.summary}")
    print(f"Bericht geschrieben nach: {output_path}")


if __name__ == "__main__":
    main()
