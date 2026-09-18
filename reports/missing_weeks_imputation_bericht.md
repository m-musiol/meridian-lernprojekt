# Behandlung fehlender Wochen (vorgezogener Teil von Stufe 4)

Betrifft die in Stufe 1 bewusst eingebauten Meldeluecken bei Out_of_Home/Radio (siehe Gate 1, `reports/stage_gates/stage2_eignungsbericht.md`, 🟡 GELB). Rohdaten (`data/raw/`) bleiben unveraendert; die bereinigte Version liegt in `data/interim/nordpunkt_synthetic/media_clean.csv`.

## Methode

Lineare Interpolation je (Geo, Kanal) entlang der Zeit: fehlende Werte werden aus dem nächsten bekannten Wert davor und danach linear geschaetzt (`pandas.Series.interpolate`). Fehlt der erste oder letzte Zeitpunkt einer Reihe (kein zweiter Stuetzpunkt fuer eine Gerade vorhanden), wird stattdessen der naechste bekannte Wert uebernommen (Randfall-Fill). Jede veraenderte Zelle ist in `<spalte>_imputed` (bool) markiert, Randfaelle zusaetzlich in `<spalte>_imputed_boundary_fill`.

**Warum lineare Interpolation und nicht Null-Fill oder Mittelwert?** Die Luecken sind einzelne, zufaellig verteilte Wochen (keine zusammenhaengenden Ausfallperioden), waehrend Spend/Impressions von Woche zu Woche eher graduell schwanken (Saisonalitaet, Trend). Null-Fill wuerde eine reale Kampagnenwoche als "kein Spend" vortaeuschen und die Spend-Varianz (Stufe-2-Check) kuenstlich verzerren; lineare Interpolation bewahrt den lokalen Verlauf am besten, ohne neue Information zu erfinden.

## Umfang der Aenderung

| Kanal | Spalte | fehlende Zellen | davon interpoliert | davon Randfall-Fill |
|---|---|---|---|---|
| Out_of_Home | spend_eur | 80 | 80 | 0 |
| Radio | spend_eur | 80 | 79 | 1 |
| Out_of_Home | impressions | 80 | 79 | 1 |
| Radio | impressions | 80 | 80 | 0 |

Die `_imputed`-Flags bleiben in `media_clean.csv` erhalten, damit Stufe 4 (Unified-Schema-Mapping) und spaetere Diagnostik (Stufe 7) erkennen koennen, welche Beobachtungen ergaenzt statt gemessen sind.
