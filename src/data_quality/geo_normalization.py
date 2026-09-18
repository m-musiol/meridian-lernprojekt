"""Pro-Kopf-Normalisierung von Geo-Wochen-Spend — geteilte Basis fuer Stufe 2 (Checks) und

Stufe 3 (EDA-Charts), damit beide exakt dieselbe Kollinearitaets-/Korrelationsberechnung nutzen.

Ohne Pro-Kopf-Normalisierung korrelieren praktisch alle Kanaele stark miteinander, weil grosse
Geos bei JEDEM Kanal automatisch mehr ausgeben als kleine — das ist reiner Groesseneffekt, keine
echte Kollinearitaet (siehe docs/entscheidungsprotokoll.md, Stufe-2-Lernpunkte).
"""

import numpy as np
import pandas as pd


def geo_week_spend_per_capita_matrix(media_df: pd.DataFrame, geo_df: pd.DataFrame) -> pd.DataFrame:
    """Kanal-Spend pro Kopf je (Geo, Woche)-Beobachtung — die Granularitaet, auf der Meridian

    tatsaechlich schaetzt.
    """
    merged = media_df.merge(geo_df[["geo", "population"]], on="geo")
    merged["spend_per_capita"] = merged["spend_eur"] / merged["population"]
    return merged.pivot_table(index=["geo", "time"], columns="channel", values="spend_per_capita").fillna(0)


def compute_vif(matrix_df: pd.DataFrame) -> dict:
    """Variance Inflation Factor je Spalte via manueller OLS-Regression (kein statsmodels-Bedarf)."""
    cols = list(matrix_df.columns)
    x_full = matrix_df.to_numpy()
    vif = {}
    for i, col in enumerate(cols):
        y = x_full[:, i]
        x_others = np.delete(x_full, i, axis=1)
        x_design = np.column_stack([np.ones(len(y)), x_others])
        coefs, *_ = np.linalg.lstsq(x_design, y, rcond=None)
        y_hat = x_design @ coefs
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        vif[col] = 1 / (1 - r2) if r2 < 0.999 else float("inf")
    return vif
