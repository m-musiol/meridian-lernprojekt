# Stufe 1 — Bericht: Synthetischer Nordpunkt-Datensatz (Datenquelle 2)

Dieser Bericht wird automatisch bei jedem Lauf von `generate_nordpunkt_data.py` neu erzeugt (nicht von Hand editieren — Aenderungen bitte im Skript vornehmen, siehe `write_report()`).

## 1. Erzeugungs-Parameter (Stellschrauben)

Diese Werte werden beim Aufruf des Skripts per CLI-Flag gesetzt (siehe `--help`) und bestimmen Umfang und Schwierigkeitsgrad der generierten Daten:

- **Seed:** `42` — Startwert des Zufallsgenerators. Gleicher Seed + gleiche Parameter = exakt reproduzierbare Daten (Pflicht laut `CLAUDE.md`, Punkt 7).
- **Geos:** 10 — Anzahl simulierter Regionen. Mehr Geos = mehr Beobachtungen fuer die spaetere Modellschaetzung, aber auch mehr Parameter (siehe Gate-1-Heuristik in Stufe 2).
- **Wochen:** 156 — Laenge der Zeitreihe. Zu kurz erschwert es, langsam wirkende Adstock-Effekte (z.B. TV) und Jahressaisonalitaet ueberhaupt zu erkennen.
- **Start:** 2021-01-04 — erster Wochenmontag der Zeitreihe.
- **Jahresbudget:** 10,000,000 EUR — nationales Media-Gesamtbudget pro Jahr, auf die Kanaele gemaess `annual_budget_share` in `config.py` aufgeteilt.

## 2. Kanal-Kennzahlen: Ground Truth

"Ground Truth" heisst hier: die *wahren*, beim Generieren fest vorgegebenen Effektstaerken — in echten Projekten unbekannt, hier bewusst bekannt, um spaeter (Stufe 8) zu pruefen, ob das trainierte Meridian-Modell sie aus den Daten korrekt zurueckgewinnt ("Parameter Recovery").

| Kanal | Spend gesamt (EUR) | Ziel-ROI | realisierter ROI | Adstock-Decay | Hill-Slope | Hill-EC50 |
|---|---|---|---|---|---|---|
| TV | 9,954,699 | 1.50 | 1.50 | 0.60 | 1.50 | 2,331,481 |
| Video_YouTube | 1,486,999 | 1.40 | 1.40 | 0.30 | 1.20 | 167,496 |
| Programmatic_Display | 4,631,473 | 1.20 | 1.20 | 0.20 | 1.00 | 1,300,382 |
| Paid_Social | 5,013,872 | 2.00 | 2.00 | 0.25 | 1.30 | 981,629 |
| Paid_Search_Brand | 2,880,876 | 4.00 | 4.00 | 0.10 | 1.00 | 172,934 |
| Paid_Search_NonBrand | 4,722,678 | 2.50 | 2.50 | 0.15 | 1.00 | 331,108 |
| Affiliate | 1,615,948 | 2.00 | 2.00 | 0.20 | 1.00 | 189,210 |
| Out_of_Home | 1,485,140 | 1.00 | 1.00 | 0.40 | 1.20 | 528,561 |
| Radio | 1,829,640 | 1.10 | 1.10 | 0.50 | 1.20 | 593,760 |

### Wie werden diese Kennzahlen berechnet, und was sagen sie aus?

- **Spend gesamt:** Summe von `spend_eur` ueber alle Geos und Wochen (fehlende Wochen zaehlen als 0). Zeigt die Groessenordnung des Kanals im Media-Mix.
- **Adstock-Decay** (0–1): woechentliche "Retention-Rate" der Werbewirkung. Formel: `adstocked[t] = exposure[t] + decay * adstocked[t-1]` (siehe `transforms.apply_adstock`). Ein Wert von 0,6 (TV) bedeutet: 60 % der Wirkung einer Woche schwappen in die Folgewoche rueber, bei 0,1 (Paid Search Brand) ist der Effekt fast schon nach einer Woche verpufft — Suchintention ist kurzlebig, TV-Markenwirkung haelt laenger an.
- **Hill-Slope & Hill-EC50:** beschreiben gemeinsam die Saettigungskurve `saturation = adstocked^slope / (adstocked^slope + ec50^slope)` (siehe `transforms.hill_saturation`), Ergebnis zwischen 0 und 1. `Hill-EC50` ist der Halbsaettigungspunkt: bei diesem (adstockten) Exposure-Niveau ist bereits 50 % der maximal moeglichen Kanalwirkung erreicht — je hoeher der bisherige Spend im Verhaeltnis zum EC50, desto staerker die abnehmenden Grenzertraege. `Hill-Slope` steuert, wie abrupt dieser Uebergang von "linear wachsend" zu "gesaettigt" verlaeuft (hoeherer Wert = schaerferer Knick).
- **Ziel-ROI vs. realisierter ROI:** `Ziel-ROI` ist die in `config.py` vorgegebene Wunsch-Kennzahl (Umsatz in EUR je ausgegebenem Euro). Waehrend der Generierung wird daraus ein Skalierungsfaktor (`max_revenue_effect`) berechnet, mit dem die Saettigungskurve so skaliert wird, dass `realisierter ROI = Summe(Umsatzbeitrag) / Summe(Spend)` moeglichst genau dem Ziel entspricht (siehe `compute_channel_contributions`). Beide Werte sollten daher (fast) identisch sein — eine spuerbare Abweichung waere ein Hinweis auf einen Rechenfehler in der Kalibrierung.

## 3. Bewusster Noise-Layer (relevant fuer Stufe 2)

Reale Mediadaten sind nie perfekt — deshalb baut der Generator zwei typische Praxisprobleme absichtlich ein, damit die Datenqualitaetspruefung in Stufe 2 nicht trivial "gruen" ausfaellt:

- **Fehlende Wochen bei Out_of_Home:** 5.1% der Geo-Wochen sind `NaN` (zufaellig je Geo ausgewaehlt, simuliert unvollstaendige Kanal-Meldungen/Datenlieferung).
- **Fehlende Wochen bei Radio:** 5.1% der Geo-Wochen sind `NaN` (zufaellig je Geo ausgewaehlt, simuliert unvollstaendige Kanal-Meldungen/Datenlieferung).
- **TV↔Radio-Spend-Korrelation:** 0.589 (Pearson-Korrelation des Spends pro Kopf je Geo-Woche — absolute EUR-Werte wuerden vor allem den Geo-Groesseneffekt messen, siehe `compute_noise_layer_metrics`). Radio behaelt sein eigenes Budget, aber ein Teil seiner Verteilung ueber Geo/Zeit folgt bewusst dem TV-Muster (`derive_radio_spend`), weil Media-Planer beide Kanaele in der Praxis oft gemeinsam takten — das erschwert es einem Modell, die Einzelwirkung beider Kanaele sauber zu trennen (Multikollinearitaet, klassischer VIF-Kandidat in Stufe 2). Hoechste Korrelation unter allen anderen Kanalpaaren: Paid_Search_NonBrand<->Paid_Social = 0.525 — spuerbar niedriger, da dort nur die gemeinsame (leicht kanal-spezifisch verschobene) Saisonalitaet durchschlaegt, nicht die gezielte Kopplung.

## 4. Verteilung der Zielgroessen (KPIs)

Werte je Geo-Woche, nach der Kombination aus Baseline + Kanalbeitraegen + Kontrolleffekten + multiplikativem Messrauschen (`noise_sigma`):

| KPI | Minimum | Median | Mittelwert | Maximum |
|---|---|---|---|---|
| Revenue (EUR) | 103,669 | 360,791 | 363,831 | 778,694 |
| Website-Sessions | 2,806 | 8,875 | 9,041 | 19,961 |

Keine negativen Werte moeglich (durch `np.clip` vor dem Rauschen abgesichert). Die Spanne zwischen Minimum und Maximum entsteht durch die Kombination aus unterschiedlich grossen Geos (Bevoelkerung), Saisonalitaet (Q1-/Q4-Peaks) und den Media-/Kontrolleffekten — genau diese Variation braucht ein MMM-Modell spaeter, um Kanalwirkungen ueberhaupt schaetzen zu koennen.

## 5. Ausgabedateien

- `data/raw/nordpunkt_synthetic/media.csv` — Spend/Impressions/Reach/Frequency je Geo, Woche, Kanal (Long-Format).
- `data/raw/nordpunkt_synthetic/controls_kpi.csv` — Controls, Organic-/Non-Media-Signale und beide KPIs je Geo/Woche.
- `data/raw/nordpunkt_synthetic/geo_population.csv` — Bevoelkerung und Bevoelkerungsanteil je Geo.
- `data/ground_truth/nordpunkt_ground_truth.json` — alle wahren Parameter maschinenlesbar (fuer den Modell-vs-Wahrheit-Vergleich in Stufe 8).