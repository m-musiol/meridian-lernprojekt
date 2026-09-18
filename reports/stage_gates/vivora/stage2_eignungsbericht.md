# Stufe 2 — Eignungsbericht (Gate 1)

Kunde: **Vivora Sport & Fitness** (vivora). Datengrundlage: `data/raw/vivora_synthetic/`.

## Gesamtvotum: 🟡 **GELB — mit dokumentierten Einschraenkungen weiter zu Stufe 3.** Limitierungen muessen in `docs/model_card.md` vermerkt werden.

## Kriterien im Detail

| Ampel | Kriterium | Messwert | Begruendung des Schwellenwerts | Empfehlung |
|---|---|---|---|---|
| 🟢 | Vollstaendigkeit (fehlende Wochen je Kanal) | Groesste Luecke: 0.0%. Betroffene Kanaele: keine. | Faustregel: <2% gruen (vernachlaessigbar), 2-10% gelb (dokumentieren/imputieren), >10% rot (Kanal ggf. ausschliessen oder Daten nachliefern). | — |
| 🟢 | Granularitaet (Wochenebene, Geo-Zuordnung) | Wochentakt durchgehend: True. Alle Geos bekannt: True. | Meridian erwartet konsistente Zeit- und Geo-Achsen; unregelmaessige Zeitschritte oder unbekannte Geos machen das Input-Array-Mapping (Stufe 4) unmoeglich. | — |
| 🟢 | Zeitraumlaenge vs. Modellkomplexitaet | 936 Beobachtungen (Geos x Wochen) vs. ca. 33 Parameter (7 Kanaele + 6 Controls + 20 geschaetzte Knots) = Verhaeltnis 28.4. | Grobe Faustregel aus der Meridian-Doku (kein Hard-Cutoff): Verhaeltnis >20 gruen (komfortabel), 10-20 gelb (machbar, aber wenig Puffer fuer Geo-Hierarchie-Varianz), <10 rot (Ueberparametrisierung wahrscheinlich, Konvergenzprobleme zu erwarten). | — |
| 🟡 | Spend-Varianz je Kanal (Variationskoeffizient) | Niedrigster Variationskoeffizient: Programmatic_Display mit CV=0.23. | Faustregel: CV>0.3 gruen (genug Schwankung, um den Kanaleffekt vom Rauschen zu trennen), 0.15-0.3 gelb, <0.15 rot (nahezu konstanter Spend erschwert Identifikation der Saettigungskurve). | Fuer Programmatic_Display: Spend-Schwankung pruefen (z.B. bewusste Flighting-Perioden), sonst Priors in Stufe 5 enger fassen, um Nichtidentifizierbarkeit abzufedern. |
| 🟢 | Kollinearitaet zwischen Kanaelen (Korrelation/VIF) | Hoechste Korrelation: App_Install_Ads<->Paid_Search_NonBrand = 0.69. Hoechster VIF: App_Install_Ads = 4.5. | Berechnet auf Geo-Wochen-Ebene pro Kopf (nicht national aggregiert, nicht in absoluten EUR), da absolute Spend-Werte sonst nur den Geo-Groesseneffekt messen wuerden statt echter zeitlicher Kollinearitaet. Faustregel VIF: <5 gruen, 5-10 gelb (beobachten), >10 rot (klassischer Schwellenwert fuer problematische Multikollinearitaet — der Kanaleffekt laesst sich kaum noch vom korrelierten Nachbarkanal trennen). | — |
| 🟢 | Ausreisser & Einheiten-Konsistenz | Negativer Spend: 0, negative KPI-Werte: 0, IQR-Ausreisser (>3x IQR): 1 von 6552 Zeilen (0.0%). | Negative Spend-/KPI-Werte sind ein Hard-Fail (Einheiten-Inkonsistenz). Ausreisser-Anteil per 3x-IQR-Regel: <1% gruen, 1-3% gelb (pruefen, meist echte Kampagnenspitzen), >3% rot. | — |
| 🟢 | Verfuegbarkeit Kontrollvariablen | Controls: ['price_index', 'promo_flag', 'holiday_flag', 'temperature_c', 'consumer_climate_index', 'competitor_spend_proxy_eur']. Fehlende Spalten: keine. max. Lueckenanteil 0.0%. | Kontrollvariablen sind noetig, um Confounder (z.B. Preis, Promotion, Saisonalitaet) von der Media-Wirkung zu trennen — ohne sie droht Overattribution auf Media. | — |
| 🟢 | Geo-Populationsdaten | 6/6 Geos mit Populationswert, alle positiv: True. | Pflicht fuer ein Geo-Modell — Meridian nutzt die Population zur Skalierung von Baseline und Kanaleffekten zwischen Geos. | — |
| 🟢 | Reach/Frequency-Verfuegbarkeit | Automatisch erkannte R/F-Kanaele: ['Paid_Social', 'Influencer']. | Keine vordeklarierte Kanalliste vorhanden — es wird nur berichtet, welche Kanaele tatsaechlich Reach/Frequency-Daten liefern. | — |

## Fuer die Model Card zu dokumentierende Limitierungen

- **Spend-Varianz je Kanal (Variationskoeffizient)** (🟡): Fuer Programmatic_Display: Spend-Schwankung pruefen (z.B. bewusste Flighting-Perioden), sonst Priors in Stufe 5 enger fassen, um Nichtidentifizierbarkeit abzufedern.