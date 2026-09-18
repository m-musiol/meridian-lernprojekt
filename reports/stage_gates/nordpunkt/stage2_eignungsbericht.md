# Stufe 2 — Eignungsbericht (Gate 1)

Kunde: **Nordpunkt Home & Living** (nordpunkt). Datengrundlage: `data/raw/nordpunkt_synthetic/`.

## Gesamtvotum: 🟡 **GELB — mit dokumentierten Einschraenkungen weiter zu Stufe 3.** Limitierungen muessen in `docs/model_card.md` vermerkt werden.

## Kriterien im Detail

| Ampel | Kriterium | Messwert | Begruendung des Schwellenwerts | Empfehlung |
|---|---|---|---|---|
| 🟡 | Vollstaendigkeit (fehlende Wochen je Kanal) | Groesste Luecke: 5.1%. Betroffene Kanaele: {'Out_of_Home': 0.051, 'Radio': 0.051}. | Faustregel: <2% gruen (vernachlaessigbar), 2-10% gelb (dokumentieren/imputieren), >10% rot (Kanal ggf. ausschliessen oder Daten nachliefern). | Fehlende Wochen vor Stufe 4 explizit behandeln (Interpolation oder Null-Fill mit Flag) und als Limitierung in der Model Card vermerken. |
| 🟢 | Granularitaet (Wochenebene, Geo-Zuordnung) | Wochentakt durchgehend: True. Alle Geos bekannt: True. | Meridian erwartet konsistente Zeit- und Geo-Achsen; unregelmaessige Zeitschritte oder unbekannte Geos machen das Input-Array-Mapping (Stufe 4) unmoeglich. | — |
| 🟢 | Zeitraumlaenge vs. Modellkomplexitaet | 1560 Beobachtungen (Geos x Wochen) vs. ca. 35 Parameter (9 Kanaele + 6 Controls + 20 geschaetzte Knots) = Verhaeltnis 44.6. | Grobe Faustregel aus der Meridian-Doku (kein Hard-Cutoff): Verhaeltnis >20 gruen (komfortabel), 10-20 gelb (machbar, aber wenig Puffer fuer Geo-Hierarchie-Varianz), <10 rot (Ueberparametrisierung wahrscheinlich, Konvergenzprobleme zu erwarten). | — |
| 🟢 | Spend-Varianz je Kanal (Variationskoeffizient) | Niedrigster Variationskoeffizient: Programmatic_Display mit CV=0.44. | Faustregel: CV>0.3 gruen (genug Schwankung, um den Kanaleffekt vom Rauschen zu trennen), 0.15-0.3 gelb, <0.15 rot (nahezu konstanter Spend erschwert Identifikation der Saettigungskurve). | — |
| 🟢 | Kollinearitaet zwischen Kanaelen (Korrelation/VIF) | Hoechste Korrelation: Radio<->TV = 0.59. Hoechster VIF: Paid_Search_NonBrand = 2.2. | Berechnet auf Geo-Wochen-Ebene pro Kopf (nicht national aggregiert, nicht in absoluten EUR), da absolute Spend-Werte sonst nur den Geo-Groesseneffekt messen wuerden statt echter zeitlicher Kollinearitaet. Faustregel VIF: <5 gruen, 5-10 gelb (beobachten), >10 rot (klassischer Schwellenwert fuer problematische Multikollinearitaet — der Kanaleffekt laesst sich kaum noch vom korrelierten Nachbarkanal trennen). | — |
| 🟢 | Ausreisser & Einheiten-Konsistenz | Negativer Spend: 0, negative KPI-Werte: 0, IQR-Ausreisser (>3x IQR): 0 von 14040 Zeilen (0.0%). | Negative Spend-/KPI-Werte sind ein Hard-Fail (Einheiten-Inkonsistenz). Ausreisser-Anteil per 3x-IQR-Regel: <1% gruen, 1-3% gelb (pruefen, meist echte Kampagnenspitzen), >3% rot. | — |
| 🟢 | Verfuegbarkeit Kontrollvariablen | Controls: ['price_index', 'promo_flag', 'holiday_flag', 'temperature_c', 'consumer_climate_index', 'competitor_spend_proxy_eur']. Fehlende Spalten: keine. max. Lueckenanteil 0.0%. | Kontrollvariablen sind noetig, um Confounder (z.B. Preis, Promotion, Saisonalitaet) von der Media-Wirkung zu trennen — ohne sie droht Overattribution auf Media. | — |
| 🟢 | Geo-Populationsdaten | 10/10 Geos mit Populationswert, alle positiv: True. | Pflicht fuer ein Geo-Modell — Meridian nutzt die Population zur Skalierung von Baseline und Kanaleffekten zwischen Geos. | — |
| 🟢 | Reach/Frequency-Verfuegbarkeit | Abdeckung je erwartetem R/F-Kanal: {'TV': True, 'Paid_Social': True}. | Client-Config verlangt Reach/Frequency fuer diese Kanaele (feinere Frequenzmodellierung). | — |

## Fuer die Model Card zu dokumentierende Limitierungen

- **Vollstaendigkeit (fehlende Wochen je Kanal)** (🟡): Fehlende Wochen vor Stufe 4 explizit behandeln (Interpolation oder Null-Fill mit Flag) und als Limitierung in der Model Card vermerken.