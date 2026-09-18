"""Behandelt die bewusst eingebauten fehlenden Wochen bei Out_of_Home/Radio (Gate 1, gelb).

Vorgezogener Teil von Stufe 4 (Feature Engineering): Rohdaten (`data/raw/`) bleiben unveraendert,
die bereinigte Version landet in `data/interim/`. Methode: lineare Interpolation je (Geo, Kanal)
entlang der Zeit fuer Luecken zwischen zwei bekannten Werten; Randfaelle (erste/letzte Woche fehlt,
wo keine zwei Stuetzpunkte fuer eine Gerade vorhanden sind) werden mit dem naechsten bekannten Wert
aufgefuellt. Jede veraenderte Zelle wird in einer `_imputed`-Flag-Spalte markiert, damit spaetere
Schritte (und das Modell-Team) echte von ergaenzten Werten unterscheiden koennen.
"""

import argparse
import pathlib

import pandas as pd

VALUE_COLUMNS = ("spend_eur", "impressions")


def impute_group(group: pd.DataFrame) -> pd.DataFrame:
    """Pandas' interpolate() extrapoliert Rand-NaNs bereits selbst (konstant), daher wird der

    Randfall strukturell bestimmt (vor dem ersten bzw. nach dem letzten gueltigen Wert), statt
    danach zu pruefen, ob interpolate() noch NaN uebrig gelassen hat.
    """
    group = group.sort_values("time").reset_index(drop=True)
    for col in VALUE_COLUMNS:
        was_missing = group[col].isna()
        first_valid = group[col].first_valid_index()
        if first_valid is None:
            is_boundary = was_missing
        else:
            last_valid = group[col].last_valid_index()
            is_boundary = was_missing & ((group.index < first_valid) | (group.index > last_valid))

        group[col] = group[col].interpolate(method="linear", limit_direction="both").bfill().ffill()
        group[f"{col}_imputed"] = was_missing
        group[f"{col}_imputed_boundary_fill"] = is_boundary
    return group


def summarize(media_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in VALUE_COLUMNS:
        by_channel = media_df.groupby("channel")[col].apply(lambda s: int(s.isna().sum()))
        for channel, n_missing in by_channel[by_channel > 0].items():
            n_boundary = int(cleaned_df.loc[cleaned_df["channel"] == channel, f"{col}_imputed_boundary_fill"].sum())
            rows.append({
                "channel": channel, "spalte": col, "fehlende_zellen": n_missing,
                "davon_randfall_fill": n_boundary, "davon_linear_interpoliert": n_missing - n_boundary,
            })
    return pd.DataFrame(rows)


def write_report(summary: pd.DataFrame, output_path: pathlib.Path) -> None:
    lines = [
        "# Behandlung fehlender Wochen (vorgezogener Teil von Stufe 4)\n",
        "Betrifft die in Stufe 1 bewusst eingebauten Meldeluecken bei Out_of_Home/Radio "
        "(siehe Gate 1, `reports/stage_gates/stage2_eignungsbericht.md`, 🟡 GELB). "
        "Rohdaten (`data/raw/`) bleiben unveraendert; die bereinigte Version liegt in "
        "`data/interim/nordpunkt_synthetic/media_clean.csv`.\n",
        "## Methode\n",
        "Lineare Interpolation je (Geo, Kanal) entlang der Zeit: fehlende Werte werden aus dem "
        "nächsten bekannten Wert davor und danach linear geschaetzt (`pandas.Series.interpolate`). "
        "Fehlt der erste oder letzte Zeitpunkt einer Reihe (kein zweiter Stuetzpunkt fuer eine "
        "Gerade vorhanden), wird stattdessen der naechste bekannte Wert uebernommen "
        "(Randfall-Fill). Jede veraenderte Zelle ist in `<spalte>_imputed` (bool) markiert, "
        "Randfaelle zusaetzlich in `<spalte>_imputed_boundary_fill`.\n",
        "**Warum lineare Interpolation und nicht Null-Fill oder Mittelwert?** Die Luecken sind "
        "einzelne, zufaellig verteilte Wochen (keine zusammenhaengenden Ausfallperioden), waehrend "
        "Spend/Impressions von Woche zu Woche eher graduell schwanken (Saisonalitaet, Trend). "
        "Null-Fill wuerde eine reale Kampagnenwoche als \"kein Spend\" vortaeuschen und die "
        "Spend-Varianz (Stufe-2-Check) kuenstlich verzerren; lineare Interpolation bewahrt den "
        "lokalen Verlauf am besten, ohne neue Information zu erfinden.\n",
        "## Umfang der Aenderung\n",
        "| Kanal | Spalte | fehlende Zellen | davon interpoliert | davon Randfall-Fill |",
        "|---|---|---|---|---|",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['channel']} | {row['spalte']} | {row['fehlende_zellen']} | "
            f"{row['davon_linear_interpoliert']} | {row['davon_randfall_fill']} |"
        )
    lines.append(
        "\nDie `_imputed`-Flags bleiben in `media_clean.csv` erhalten, damit Stufe 4 "
        "(Unified-Schema-Mapping) und spaetere Diagnostik (Stufe 7) erkennen koennen, welche "
        "Beobachtungen ergaenzt statt gemessen sind.\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Interpoliert fehlende Media-Wochen (Out_of_Home/Radio).")
    parser.add_argument("--input", default="data/raw/nordpunkt_synthetic/media.csv")
    parser.add_argument("--output", default="data/interim/nordpunkt_synthetic/media_clean.csv")
    parser.add_argument("--report", default="reports/missing_weeks_imputation_bericht.md")
    args = parser.parse_args()

    media_df = pd.read_csv(args.input, parse_dates=["time"])
    cleaned_df = media_df.groupby(["geo", "channel"], group_keys=True).apply(
        impute_group, include_groups=False
    ).reset_index(level=["geo", "channel"]).reset_index(drop=True)

    remaining_na = cleaned_df[list(VALUE_COLUMNS)].isna().sum().sum()
    if remaining_na:
        raise ValueError(f"Nach Imputation sind noch {remaining_na} Zellen NaN — Randfall-Logik pruefen.")

    output_path = pathlib.Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_df.to_csv(output_path, index=False)

    summary = summarize(media_df, cleaned_df)
    write_report(summary, pathlib.Path(args.report))

    print(f"Bereinigt: {output_path} ({len(cleaned_df)} Zeilen, 0 verbleibende NaN)")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
