# Unified Input Schema

> Format, das jeder Kunde (synthetisch generiert ODER per Upload) einhalten muss, damit Stufe 2
> (Datenqualitaetspruefung) und Stufe 3 (EDA) generisch darauf laufen koennen. Die synthetischen
> Demo-Kunden (`clients/nordpunkt/`, `clients/vivora/`) erzeugen dieses Format automatisch; beim
> Hochladen eigener Daten (Streamlit-App) muss es von Hand hergestellt werden.

## `media.csv` (Long-Format: eine Zeile je Geo, Woche, Kanal)

| Spalte | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `geo` | Text | ja | Geo-Bezeichner, muss zu `geo_population.csv` passen. |
| `time` | Datum | ja | Wochenanfang, durchgehend woechentlich (z.B. immer Montag). |
| `channel` | Text | ja | Kanalname (frei waehlbar, z.B. `TV`, `Meta_Ads`). |
| `spend_eur` | Zahl ≥ 0 | ja | Media-Spend in der Waehrung des Kunden (Spaltenname bleibt `spend_eur`, auch bei anderer Waehrung). |
| `impressions` | Zahl ≥ 0 | ja | Exposure-Metrik (Impressions, Clicks o.ae.). |
| `reach` | Zahl ≥ 0 | nein | Nur fuer Kanaele mit Reach/Frequency-Tracking. Fehlt die Spalte oder ist sie leer, erkennt Stufe 2 den Kanal automatisch als "ohne R/F". |
| `frequency` | Zahl ≥ 0 | nein | Siehe `reach`. |

Fehlende Wochen sind erlaubt (als leere Zelle) — Stufe 2 meldet den Anteil, Stufe 4
(`src/features/handle_missing_media_weeks.py`) kann sie interpolieren.

## `controls_kpi.csv` (eine Zeile je Geo, Woche)

| Spalte | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `geo` | Text | ja | Wie in `media.csv`. |
| `time` | Datum | ja | Wie in `media.csv`. |
| `population` | Zahl > 0 | empfohlen | Falls vorhanden, wird sie bevorzugt aus `geo_population.csv` genommen. |
| *(primaere KPI-Spalte)* | Zahl | ja | Name frei waehlbar (z.B. `revenue_eur`, `orders`) — wird beim Upload explizit ausgewaehlt. |
| *(sekundaere KPI-Spalte)* | Zahl | nein | Optional, ebenfalls frei benennbar (z.B. `app_installs`). |
| *(beliebig viele weitere Spalten)* | Zahl/Flag | nein | Werden automatisch als Kontrollvariablen erkannt (alles ausser `geo`/`time`/`population`/KPI-Spalten). |

## `geo_population.csv` (eine Zeile je Geo)

| Spalte | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `geo` | Text | ja | Eindeutiger Geo-Bezeichner. |
| `population` | Zahl > 0 | ja | Bevoelkerung/Marktgroesse — Pflicht fuer ein Geo-Modell (Gate-1-Check). |
| `pop_share` | Zahl (0-1) | nein | Wird bei Bedarf aus `population` berechnet. |

## Warum dieses Format?

Alle Checks (`src/data_quality/checks.py`) und Charts (`src/visualization/charts.py`) arbeiten
generisch auf diesen Spaltennamen/-formen — nicht auf einer festen Kanal- oder Kontrollvariablen-
Liste. Ein Kunde mit anderen Kanaelen, anderer KPI-Benennung oder anderer Geo-Anzahl braucht daher
**keinen Code-Change**, nur Daten in diesem Format (siehe `clients/vivora/config.py` als Beleg:
komplett andere Kanaele/KPI-Namen, gleiche Pipeline).
