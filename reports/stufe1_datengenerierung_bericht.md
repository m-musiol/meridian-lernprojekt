# Stufe 1 — Bericht: Synthetischer Nordpunkt-Datensatz (Datenquelle 2)

Seed: `42` | Geos: 10 | Wochen: 156 | Start: 2021-01-04 | Jahresbudget: 10,000,000 EUR


## Ground-Truth-ROI je Kanal (realisiert vs. Ziel)

| Kanal | Ziel-ROI | realisiert | Adstock-Decay | Hill-Slope |
|---|---|---|---|---|
| TV | 1.50 | 1.50 | 0.60 | 1.50 |
| Video_YouTube | 1.40 | 1.40 | 0.30 | 1.20 |
| Programmatic_Display | 1.20 | 1.20 | 0.20 | 1.00 |
| Paid_Social | 2.00 | 2.00 | 0.25 | 1.30 |
| Paid_Search_Brand | 4.00 | 4.00 | 0.10 | 1.00 |
| Paid_Search_NonBrand | 2.50 | 2.50 | 0.15 | 1.00 |
| Affiliate | 2.00 | 2.00 | 0.20 | 1.00 |
| Out_of_Home | 1.00 | 1.00 | 0.40 | 1.20 |
| Radio | 1.10 | 1.10 | 0.50 | 1.20 |

Ausgabe: `data/raw/nordpunkt_synthetic/` (media.csv, controls_kpi.csv), Ground Truth: `data/ground_truth/`.
