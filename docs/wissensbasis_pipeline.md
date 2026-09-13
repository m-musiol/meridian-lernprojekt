# Wissensbasis: Datenstrategie, Pipeline, Personas, Automatisierung, Glossar

> Ablageort im Repo: `docs/wissensbasis_pipeline.md`. Wird von `CLAUDE.md` per `@docs/wissensbasis_pipeline.md`
> referenziert und damit automatisch mitgeladen. Dieses Dokument enthält das fachliche Detailwissen zum
> Meridian-Lernprojekt — die schlanke `CLAUDE.md` enthält nur die verbindlichen Kernregeln und verweist hierher.

---

## 1. Datenstrategie (kein echtes Kundenszenario)

Fiktiver Kontext für alle Übungen: Marke **"Nordpunkt Home & Living"**, D-A-CH-Möbel-/Wohnaccessoires-Retailer
mit Online- und stationärem Vertrieb. Dieser Rahmen ist frei erfunden und darf nie mit realen Marken verwechselbar
gemacht werden.

Drei sich ergänzende Datenquellen, bewusst in dieser Reihenfolge einzusetzen:

1. **Meridians eigene simulierte Beispieldaten** (`geo_all_channels.csv` im offiziellen Repo, plus das
   `RF_Data_Simulation_for_Meridian`-Notebook) — Vorteil: bekannte Generatorwahrheit, ideal um zu lernen, ob das
   Modell die "wahren" Effekte korrekt zurückgewinnt ("Parameter Recovery"). Einsatzzweck: Phase "Modell-Mechanik
   verstehen" (Stufen 5-8, erste Durchläufe).
2. **Eigener synthetischer Generator** (`src/data_generation/`) — für den realistischen Agentur-Case. Muss
   erzeugen:
   - Geo-Ebene: deutsche Bundesländer oder eine vereinfachte DMA-ähnliche Struktur (8-12 Geo-Einheiten) plus
     Populationsgewicht pro Geo.
   - Zeitraum: mind. 104 Wochen (2 Jahre), besser 156 (3 Jahre), wöchentliche Granularität.
   - Paid-Media-Kanäle (mit Spend + Exposure-Metrik, mind. 2 Kanäle mit Reach/Frequency): TV, Video/YouTube,
     Programmatic Display, Paid Social, Paid Search Brand, Paid Search Non-Brand, Affiliate, Out-of-Home, Radio.
   - Organic Media: organische Suchklicks/Impressions, Social-Organic-Reichweite.
   - Non-Media Treatments: Distributions-/Filialanzahl, Sortimentsbreite.
   - Kontrollvariablen: Preisindex, Promotion-Flag, Saisonalität/Feiertage, Wetter (z.B. Temperatur), Konsumklima
     (Proxy), Wettbewerber-Spend-Proxy.
   - Zwei Zielgrößen: **Abverkauf/Revenue** (Haupt-KPI) und **Website-Sessions** (zweite Zielgröße — als
     eigenständiges zweites Meridian-Modell ODER als "Mediator"/Funnel-Stufe im Full-Funnel-Setup; Entscheidung
     ist Teil von Gate 1, siehe Abschnitt 2).
   - **Ground Truth**: alle wahren Effektstärken, Adstock-Decays und Sättigungsparameter werden in
     `data/ground_truth/` gespeichert, um nach dem Training "Modell vs. Wahrheit" zu vergleichen — zentrales
     Lernelement.
   - Realistischer "Noise-Layer": Messfehler, fehlende Wochen bei 1-2 Kanälen, leichte Kollinearität zwischen
     TV und Radio (typisches Praxisproblem) — bewusst einbauen, um Stufe 2 (Datenqualität) nicht trivial zu machen.
3. **Öffentliche, unbereinigte Kaggle-/Open-Data-Sets** (z.B. `nafees2006/mmm-dataset`, weitere MMM-Datensätze
   auf Kaggle) — bewusst zusätzlich verwenden, um die **Datenqualitäts-/Eignungsprüfung (Stufe 2)** an einem
   "wie es in der Praxis wirklich ankommt"-Datensatz zu üben (unbekannte Generatorwahrheit, echte Lücken/Ausreißer).

Jede Quelle wird vor Nutzung in `docs/datenquellen_register.md` mit Lizenz und Zweck eingetragen.

---

## 2. Pipeline-Stufen (Data-Science-Lifecycle) mit Gates

Jede Stufe wird als eigenständiges, wieder ausführbares Skript/Modul unter `src/` umgesetzt und schreibt einen
kurzen Ergebnis-Report nach `reports/`. 🚦 markiert verbindliche Freigabe-Gates mit dem Nutzer.

### Stufe 0 — Auftragsklärung & Stakeholder-Briefing
- **Zweck:** Business-Fragen, KPIs, Kanäle, Constraints, Erfolgskriterien wie in einem echten Agentur-Kickoff
  festlegen — inkl. Entscheidung zur Arbeitsumgebung (`CLAUDE.md` Abschnitt 3).
- **Output:** `docs/stakeholder_briefing.md` (Business-Fragen, Ziel-KPIs, Budgetrahmen, Zeitraum, Reporting-Kadenz).
- **Automatisierung:** Claude Code entwirft Vorschlag, Mensch bestätigt/passt an. 🚦 **Gate 0**.

### Stufe 1 — Datenbeschaffung
- **Zweck:** Rohdaten gemäß Abschnitt 1 generieren bzw. laden.
- **Input:** Vorgaben aus Stufe 0. **Output:** `data/raw/*`, `docs/datenquellen_register.md`.
- **Stellschrauben:** Anzahl Geos, Zeitraum, Kanalanzahl, Noise-Intensität, welche Reach/Frequency-Kanäle.
- **Automatisierung:** vollautomatisch per Skript, deterministisch via Seed.

### Stufe 2 — Datenqualitäts- & Eignungsprüfung 🚦 Gate 1
- **Zweck:** Prüfen, ob die Daten für ein Meridian-Modell grundsätzlich geeignet sind, *bevor* Modellierungszeit
  investiert wird — analog zum Agentur-Realitätscheck "können wir mit dem liefern, was der Kunde geschickt hat?".
- **Automatisierte Checks (jeweils mit Schwellenwert + Begründung):**
  - Vollständigkeit: fehlende Wochen/Geos pro Kanal.
  - Granularität: liegt Wochenebene vor, ist Geo-Zuordnung möglich?
  - Zeitraumlänge vs. Modellkomplexität: Faustregel *Anzahl Geos × Zeitpunkte* im Verhältnis zur Parameterzahl
    (Kanäle + Controls + Knots) — grobe Heuristik aus der Meridian-Doku, kein Hard-Cutoff.
  - Spend-Varianz pro Kanal (Variationskoeffizient) — zu wenig Varianz = Effekt schwer identifizierbar.
  - Kollinearität zwischen Kanälen (Korrelation/VIF) — z.B. TV/Radio-Overlap.
  - Ausreißer & Einheiten-Konsistenz (Spend ≥ 0, Summierbarkeit über Zeit/Geo).
  - Verfügbarkeit Kontrollvariablen (Confounder für Media UND KPI vorhanden?).
  - Geo-Populationsdaten vorhanden (Pflicht bei Geo-Modell).
  - Reach/Frequency-Verfügbarkeit dort, wo gewünscht.
- **Output:** `reports/stage_gates/stage2_eignungsbericht.md` mit **Ampel-Bewertung (rot/gelb/grün)** je Kriterium
  und Gesamtvotum, plus konkrete Handlungsempfehlung: *"mindestens nötig: ..."*, *"empfohlene Ergänzung: ..."*.
- **Entscheidungslogik:**
  - **Grün:** weiter zu Stufe 3.
  - **Gelb:** mit Einschränkungen weiter, Limitierungen explizit in Model Card vermerken (z.B. National- statt
    Geo-Modell, weniger Knots).
  - **Rot:** zurück zu Stufe 1 mit konkretem Ergänzungs-/Korrekturplan (z.B. synthetische Nachgenerierung fehlender
    Wochen, zusätzliche Kontrollvariable, Aggregation auf gröbere Geo-Ebene).
- 🚦 **Gate 1:** Ergebnis wird dem Nutzer vorgelegt, bevor Stufe 3 beginnt.

### Stufe 3 — Explorative Datenanalyse (EDA)
- Trends, Saisonalität, Spend-Shares je Kanal, Korrelationen, Ereignis-/Feiertagsflags, KPI-vs-Media-Zeitreihen.
- **Output:** `reports/eda_bericht.md` + Plots.

### Stufe 4 — Feature Engineering & Unified-Schema-Mapping
- Aggregation auf Wochen-/Geo-Ebene, Skalierung, Ableitung Kontrollvariablen, Reach/Frequency-Imputation falls
  nötig, Train/Holdout-Split für spätere Validierung, Mapping auf Meridians erwartete Input-Arrays
  (KPI: G×T, Paid Media: G×T×N_M, Controls: G×T×N_C, Geo-Population etc.).
- **Output:** `data/processed/*`.

### Stufe 5 — Modellspezifikation
- `ModelSpec` definieren: Priors (Default vs. eigene/ROI-kalibrierte Priors über fiktive Experiment-/Benchmarkdaten),
  Adstock- und Hill-Sättigungsannahmen, Anzahl `knots`, Geo-Hierarchie, `unique_sigma_for_each_geo`.
- Für jede Wahl: kurze Erklärung Vor-/Nachteil (z.B. mehr Knots = mehr Flexibilität, aber Overfitting-Risiko).
- **Output:** `src/modeling/model_spec.py` + Begründung in Decision Log.

### Stufe 6 — Training
- `sample_prior`, dann `sample_posterior` (NUTS/MCMC). Erst Testlauf mit reduzierten Chains/Draws, dann voller Lauf.
- **Output:** gespeichertes Modellobjekt/Trace, Trainingslog (Laufzeit, Hardware, Settings) in `docs/model_card.md`.

### Stufe 7 — Diagnostik & Validierung 🚦 Gate 2
- R-hat, Effective Sample Size, Divergences, Posterior-Predictive-Checks, Hold-out-Fehler (RMSE/MAPE), Business-
  Plausibilität der ROI-Werte (liegt in erwartbarem Korridor?).
- **Output:** `reports/stage_gates/stage7_diagnosebericht.md` mit Ampel. Bei Rot: zurück zu Stufe 5 (Priors/Spec
  anpassen) oder Stufe 2 (Daten unzureichend).
- 🚦 **Gate 2:** erst mit Freigabe weiter zu Interpretation/Reporting.

### Stufe 8 — Interpretation
- Kanalbeiträge (Contribution), ROI & mROI je Kanal, Response-/Sättigungskurven, Adstock-Decay-Visualisierung,
  Vergleich mit `ground_truth` (nur bei synthetischen Daten mit bekannter Wahrheit).

### Stufe 9 — Forecasting
- Abverkaufsprognose und Website-Traffic-Prognose (je nach Gate-0-Entscheidung: zwei Modelle oder Funnel-Ansatz),
  inkl. Szenario-Simulation (z.B. "+20% Social-Budget", "TV-Flight im Q4").

### Stufe 10 — Optimierung
- Budget-Optimizer (Meridian `BudgetOptimizer`): optimale Kanalallokation bei gegebenem/verändertem Budget,
  What-if-Szenarien, marginale ROI-basierte Umschichtungsempfehlung.
- **Output:** `docs/media_mix_empfehlung.md` — konkrete, begründete Handlungsempfehlung.

### Stufe 11 — Reporting & Stakeholder-Kommunikation 🚦 Gate 3
- Persona-spezifische Outputs (siehe Abschnitt 3), Management Summary, Rollenspiel-Verteidigung der Ergebnisse.
- 🚦 **Gate 3:** Nutzer bestätigt, dass die Kommunikationsartefakte für die Übung ausreichen, bevor das Projekt
  als "Zyklus abgeschlossen" gilt.

### Stufe 12 — Monitoring & Feedback-Loop
- Simulierter Re-Trainings-Trigger bei "neuen" Daten, Drift-Check (verändert sich ROI/Fit stark?), Kalibrierung
  mit fiktiven Inkrementalitäts-Testergebnissen als Lernübung für "Experiment-Calibration".

---

## 3. Stakeholder-Personas für Rollenspiel-Kommunikation

Claude Code kann auf Zuruf in diese Rollen schlüpfen (für Q&A-Übungen, Einwandbehandlung, Foliensprache):

| Persona | Interesse | Erwarteter Kommunikationsstil |
|---|---|---|
| **Geschäftsführung/CMO (Kunde)** | Wachstum, klare Handlungsempfehlung, ROI-Story | kurz, ergebnisorientiert, wenig Methodik |
| **Finance/Controlling** | Risiko, Konfidenzintervalle, Budgetrechtfertigung | zahlengetrieben, Unsicherheiten explizit |
| **Media-Planung/Trading Desk** | Kanal-Detail, Flighting, Umsetzbarkeit | taktisch, operative Sprache |
| **Internes Analytics/Data-Team** | Methodik, Annahmen, Modellgrenzen | fachlich-kritisch, hinterfragt Priors/Diagnostik |

Für jede Persona soll Stufe 11 ein eigenes Kurz-Dokument (`reports/stakeholder/<persona>.md`) erzeugen und auf
Wunsch eine simulierte Rückfragerunde durchspielen.

---

## 4. Automatisierung: Python, n8n, Supabase, GitHub — wer macht was

**Grundsatz:** So viel Automatisierungsgrad wie sinnvoll, aber n8n nur einsetzen, wo es echten Mehrwert hat
(Orchestrierung/Kommunikation), nicht für die eigentliche Modellrechnung.

| Aufgabe | Werkzeug | Begründung |
|---|---|---|
| Datengenerierung, Datenqualitätsprüfung, Feature Engineering, Training, Diagnose, Optimierung | **Python-Skripte** (`src/`), von Claude Code per Bash ausgeführt | Rechenintensive TensorFlow/MCMC-Schritte gehören nicht in einen Workflow-Node |
| Lokale Steuerung mehrerer Skripte | einfacher CLI-Runner/Makefile (`invoke` oder `make`) | reicht für dieses Projektvolumen, kein Overengineering mit Airflow/Prefect |
| Persistenz: verarbeitete Daten, Modell-Lauf-Metadaten (Timestamp, Priors-Hash, R-hat, ROI-Ergebnisse), Decision-Log als Tabelle | **Supabase (Postgres, Free Tier)** | ersetzt lokale CSV-Ablage für "produktionsnäheres" Gefühl, ermöglicht spätere Abfragen/Dashboards |
| Zeitgesteuerte Trigger (z.B. "wöchentlicher Datencheck") | **n8n** | klassischer Orchestrierungs-Use-Case |
| Datenqualitäts-Alerts (Gate 1/2 rot → Benachrichtigung) | **n8n** (Webhook aus Python-Skript → n8n → E-Mail/Slack) | sinnvolle Trennung: Python prüft, n8n informiert |
| Freigabe-Gates als simuliertes Stakeholder-"Approval" | **n8n** (Formular/Approval-Node, die den nächsten Schritt erst nach Klick freigibt) | übt echten Agentur-Freigabeprozess |
| Verteilung persona-spezifischer Reports | **n8n** (E-Mail/Slack-Versand aus `reports/stakeholder/`) | Übung "Ergebnisse rausschicken" ohne echte Empfänger nötig (z.B. an eigene Adresse) |
| Re-Training-Anstoß bei neuen Daten in Supabase | **n8n** (DB-Trigger → ruft lokales Webhook/Skript auf) | Stufe 12 |
| Versionierung, Nachvollziehbarkeit, "Stakeholder-Anfragen" | **GitHub** (Commits pro Stufe, Issues als simulierte Rückfragen, optional GitHub Actions für Linting/Tests) | Standard-Praxis einer Agentur/Dev-Team, über `gh` CLI von Claude Code bedienbar (siehe `CLAUDE.md` Abschnitt 4) |

Claude Code soll n8n-Workflows als exportierbare JSON-Dateien unter `n8n/workflows/` ablegen und deren Zweck in
`docs/entscheidungsprotokoll.md` begründen — **nicht** ungefragt neue n8n-Workflows einführen, ohne dass ein Gate
oder diese Tabelle das vorsieht.

---

## 5. Glossar der wichtigsten Stellschrauben (Kurzreferenz)

*(wird von Claude Code laufend ausgebaut, ausführlicher mit Beispielen)*

- **KPI** — Zielgröße (G×T), z.B. Revenue oder Sessions; muss über Zeit/Geo summierbar sein.
- **Paid Media** — Spend + Exposure-Metrik (Impressions/Clicks/Spend) je Kanal, Geo, Zeit (G×T×N_M); Pflichtinput.
- **Organic Media / Non-Media Treatments** — optionale Zusatzsignale ohne direkten Spend.
- **Controls** — Störgrößen/Confounder, die sowohl Media als auch KPI beeinflussen (Preis, Saison, Wetter, Makro).
- **Reach & Frequency** — statt einer einzelnen Exposure-Metrik: eindeutige Seher (Reach) × Impressions/Seher
  (Frequency) — feinere Modellierung des Frequenzeffekts.
- **Geo Population** — Bevölkerungsgewicht je Geo, Pflicht für Geo-Modelle zur Skalierung.
- **Adstock (Carryover/Decay)** — wie lange und wie stark eine Werbeausspielung über die Zeit nachwirkt.
- **Hill-Sättigung** — S-Kurve (ec50/slope), die abnehmende Grenzerträge bei steigendem Spend abbildet.
- **Knots** — Stützpunkte für den zeitvariierenden Intercept (Saisonalität/Trend); mehr Knots = mehr Flexibilität,
  aber Risiko der Vermischung mit Media-Effekten.
- **Priors** — Vorwissen über Parameter (z.B. ROI-Bandbreiten); Default vs. kalibriert (z.B. mit Experimentdaten).
- **Hierarchische Varianzparameter (`eta_m`, `xi_c`)** — steuern, wie stark Informationen zwischen Geos geteilt
  werden ("Partial Pooling").
- **`unique_sigma_for_each_geo`** — eigene Residualvarianz je Geo (robuster gegen laute kleine Geos, aber
  schwerere Konvergenz).
- **R-hat / ESS / Divergences** — MCMC-Konvergenzdiagnostik.
- **ROI / mROI** — Return on Investment gesamt bzw. marginal (nächster Euro Spend).
- **Response-Kurve** — inkrementeller Output als Funktion des Spends je Kanal.
- **Budget Optimizer** — errechnet optimale Kanalallokation für ein Budget unter den Modellannahmen.
