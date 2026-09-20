# Entscheidungsprotokoll — Meridian-Lernprojekt

> Lerntagebuch und Decision Log gemäß `CLAUDE.md` Abschnitt 2, Punkt 5. Jede relevante Modell- oder
> Architekturentscheidung wird hier mit Datum, Begründung und Alternativen festgehalten.

---

## 2026-09-13 — Arbeitsumgebung (Gate 0, CLAUDE.md Abschnitt 3)

**Entscheidung:** Option A — lokaler Rechner + VS Code.

**Begründung:** Für die reine Lernphase (Stufen 0-8) reicht die lokale Umgebung; volle Kontrolle, kein
Hosting-Risiko. Ein späterer Umzug auf Option B (Hostinger-VPS via VS Code Remote-SSH) bleibt jederzeit
möglich, sobald n8n-Anbindung/Automatisierung (Stufen 8-12) im Vordergrund steht, da das Repo über GitHub
synchron gehalten wird.

**Alternative geprüft:** Option B (Hostinger-VPS) — verworfen für die Startphase, da geteilte VPS-Ressourcen
bei MCMC-Training eng werden könnten und kein Automatisierungsbedarf für Stufen 0-8 besteht.

---

## 2026-09-13 — Python-Versions-Lücke

**Befund:** Lokal ist nur Python 3.9.13 (Windows-Store-Alias) verfügbar. `google-meridian` benötigt
Python 3.11 oder 3.12.

**Entscheidung:** Nutzer installiert Python 3.12 manuell von python.org. Das venv (`.venv/`) wird danach
auf dieser Version aufgesetzt (`python -m venv .venv`), `.vscode/settings.json` verweist bereits auf
`${workspaceFolder}/.venv/Scripts/python.exe`.

**Ressourcen-Kontext:** CPU Intel i7-1065G7 (4 Kerne/8 Threads), keine dedizierte GPU (nur integrierte
Intel-Grafik, kein CUDA), 15,8 GB RAM gesamt (aktuell ~4,7 GB frei), 56 GB freier Speicher. Empfehlung:
Testläufe (Stufen 0-5, reduzierte Chains/Draws) lokal auf CPU; volle NUTS/MCMC-Läufe (Stufe 6) auf
Google Colab (kostenlose GPU), siehe `CLAUDE.md` Abschnitt 4 und Punkt 11.

---

## 2026-09-13 — Repo-Struktur / Git-Isolation

**Befund:** Der übergeordnete lokale Workspace-Ordner (der alle Projektordner des Nutzers enthält) ist
selbst die Wurzel eines bestehenden, unabhängigen Git-Repos mit einem eigenen Remote. Dessen
`.gitignore` schließt jedoch pauschal fast alles aus — `meridian-lernprojekt/` wird von diesem
äußeren Repo also nicht getrackt.

**Entscheidung:** `meridian-lernprojekt/` erhält ein eigenständiges, neu initialisiertes Git-Repo
(`git init` in diesem Ordner) und ein eigenes GitHub-Repo (`gh repo create`, privat), unabhängig vom
äußeren Workspace-Repo und von anderen, unabhängigen Projekten des Nutzers dort. So bleibt dieses
Lernprojekt sauber von anderen, thematisch nicht verwandten Projekten getrennt.

---

## 2026-09-13 — Gate 0: Freigabe Stakeholder-Briefing

**Ergebnis:** 🟢 **Freigegeben.** Nutzer hat `docs/stakeholder_briefing.md` (Business-Fragen, KPIs, Kanäle,
Budgetrahmen, Zeitraum, Erfolgskriterien) ohne Änderungswünsche bestätigt. Weiter zu Stufe 1
(Datenbeschaffung/-generierung).

---

## 2026-09-13 — Übergangslösung Python-Umgebung für den Generator

**Befund:** Auf dem System-Python 3.9.13 sind pandas/numpy bereits installiert. Der eigene
Datengenerator (Datenquelle 2) braucht kein `google-meridian` und läuft damit unabhängig von der
offenen Python-3.12-Installation.

**Entscheidung:** Generator-Code wird jetzt mit dem System-Python 3.9.13 entwickelt und getestet, um
nicht auf die manuelle Python-3.12-Installation zu warten. Sobald das `.venv` mit Python 3.12 steht,
wird derselbe Code dort erneut ausgeführt (reiner pandas/numpy-Code, keine Versions-Inkompatibilität
zu erwarten). Kein dauerhafter Ersatz für das projektspezifische venv — nur Übergangslösung für Stufe 1.

---

## 2026-09-13 — Lernpunkte aus Stufe 2: zwei Mess-Artefakte im Kollinearitäts-Check korrigiert

Beim Bau des Stufe-2-Checks (`src/data_quality/checks.py`) zeigte der erste Durchlauf ein
Gesamtvotum 🔴 ROT mit sehr hohem VIF (>19) für praktisch beliebige Kanalpaare, nicht nur für das
bewusst gekoppelte TV/Radio-Paar. Ursachenanalyse ergab zwei unabhängige Mess-Artefakte — beide
lehrreich genug für dieses Lernprojekt, um sie hier festzuhalten:

1. **Geo-Größeneffekt:** Korrelation auf rohen EUR-Werten (Geo×Woche) maß hauptsächlich, dass große
   Geos bei *jedem* Kanal automatisch mehr ausgeben — TV↔Display sprang dadurch von 0.48 (pro Kopf)
   auf 0.94 (roh). **Fix:** Kollinearitäts-Check rechnet jetzt auf Spend *pro Kopf*, nicht auf
   absoluten EUR-Werten.
2. **Gemeinsamer deterministischer Trend/Saison:** Alle Kanäle nutzten identische Trend- und
   Saisonkurven im Generator — zwei monoton wachsende Zeitreihen korrelieren fast immer stark,
   unabhängig von der genauen Steigung. **Fix:** `generate_nordpunkt_data.py` gibt jedem Kanal jetzt
   eine eigene Trendrichtung (`trend_rate` kann auch negativ sein) und eine leicht phasen-/
   amplitudenverschobene Saisonkurve (`jitter_seasonal`), damit nur die *bewusst* gekoppelten Kanäle
   (TV/Radio) auffällig korrelieren, nicht der ganze Kanal-Mix.

Zusätzlich wurde `derive_radio_spend` von "TV-Spend on top addieren" (verzerrte Radios Budgetanteil
auf ~13 Mio. EUR, weit über die im Stakeholder-Briefing vorgesehenen ~5 %) auf "Radios eigenes
Budget, aber teilweise TV-Verteilungsmuster" umgestellt — budgetneutral, aber weiterhin klar
identifizierbare Kollinearität (r≈0.59, VIF≈2.2, klar höchster Wert im Kanal-Set).

**Ergebnis Gate 1 (Stufe 2, `reports/stage_gates/stage2_eignungsbericht.md`):** 🟡 **GELB** — einzige
Einschränkung sind die bewusst eingebauten ~5,1 % fehlenden Wochen bei Out-of-Home/Radio (in
`docs/model_card.md` dokumentiert). Alle anderen acht Kriterien grün. Vorgelegt zur Freigabe vor
Beginn von Stufe 3 (EDA).

---

## 2026-09-18 — Fehlende Wochen behandelt (vorgezogener Teil von Stufe 4)

**Entscheidung:** Nutzer wollte die Gate-1-Einschränkung (fehlende Wochen bei Out_of_Home/Radio) vor
Stufe 3 behoben haben, statt sie nur zu dokumentieren und weiterzuziehen. Umgesetzt per linearer
Interpolation je (Geo, Kanal) entlang der Zeit (`src/features/handle_missing_media_weeks.py`),
Randfaelle (erste/letzte Woche einer Reihe fehlt) per Fill mit dem naechsten bekannten Wert.
Rohdaten bleiben unveraendert (`data/raw/`), bereinigte Version liegt in
`data/interim/nordpunkt_synthetic/media_clean.csv` mit `_imputed`-Flags je veraenderter Zelle.

**Begruendung der Methode:** Luecken sind einzelne, zufaellig verteilte Wochen (keine
zusammenhaengenden Ausfallperioden) bei einer sonst graduell schwankenden Zeitreihe — lineare
Interpolation bewahrt den lokalen Verlauf, ohne wie Null-Fill eine falsche "kein Spend"-Woche
vorzutaeuschen oder wie Mittelwert-Fill die Spend-Varianz zu verzerren. Details/Umfang in
`reports/missing_weeks_imputation_bericht.md`.

**Prozess-Notiz:** Dieser Schritt gehoert inhaltlich zu Stufe 4 (Feature Engineering), wurde aber auf
Nutzerwunsch vorgezogen, damit Stufe 3 (EDA) auf bereits bereinigten Daten aufsetzt. Fuer Stufe 4
verbleibt noch das vollstaendige Unified-Schema-Mapping (G×T-Arrays fuer Meridian).

---

## 2026-09-18 — Multi-Client-Generalisierung (Phasen 1-3): Pipeline nicht mehr Nordpunkt-exklusiv

**Entscheidung:** Nutzer wollte die Pipeline explizit **jetzt vollstaendig** fuer beliebige Kunden
einsetzbar machen (nicht nur leichtgewichtig vormerken), plus professionelle Stakeholder-
Visualisierungen und eine Streamlit-App fuer komfortablen Upload/Interaktion (siehe Plan
`parsed-herding-swan.md`). Umgesetzt in Phasen, jede einzeln verifiziert:

- **Client-Config** (`src/client_config.py`, `clients/<id>/config.py`): `ChannelConfig` (unveraendert),
  `GeneratorSettings` (nur fuer `data_source="synthetic"`), `ClientConfig` mit
  `control_columns`/`reach_frequency_channels` = `None` als Auto-Erkennungs-Fallback (wichtig fuer
  hochgeladene Kunden ohne deklarierte Metadaten). Python-Module statt YAML gewaehlt — keine neue
  Lade-/Validierungsschicht noetig, Configs werden nur von der Entwicklerin angelegt, nicht von
  Endnutzern editiert; bei Bedarf spaeter leicht auf YAML umstellbar.
- **Import-Mechanik:** Path-Shim (`sys.path.insert(0, .../src)` + bare Import) statt `python -m` —
  keine bestehende Aufruf-Konvention aendert sich, kein `pip install -e .` noetig.
- **Generator** (`generate_nordpunkt_data.py` → `generate_synthetic_data.py --client <id>`): liest
  `ClientConfig` statt Hardcode, CLI-Flags ueberschreiben nur explizit gesetzte Felder
  (`dataclasses.replace`). Zwei Nordpunkt-Spezifika generisch gemacht, ohne die rng-Ziehungsreihenfolge
  zu aendern: Cross-Channel-Organic-Boost faellt bei fehlendem Kanal auf 0 zurueck statt KeyError;
  der Noise-Layer-Bericht findet das staerkste Kanalpaar generisch statt "TV"/"Radio" hart zu codieren.
- **Stufe 2** (`checks.py`, `run_stage2_check.py`): `control_columns`/`reach_frequency_channels` kommen
  aus der Client-Config; Pro-Kopf-Kollinearitaets-Hilfsfunktion nach `data_quality/geo_normalization.py`
  verschoben (reiner Move, von Stufe 3 mitnutzbar).
- **Wochen-Imputation** (`handle_missing_media_weeks.py`): `--client`-Flag, Pfade aus Client-Config.
- **Pfad-Namespacing (Bugfix):** `reports/{client_id}/...`, `reports/stage_gates/{client_id}/...`,
  `data/interim/{client_id}/...` — vorher generische Pfade haetten ein zweiter Kunde stillschweigend
  ueberschrieben. Alte Nordpunkt-Reports per `git mv` in die neuen Pfade verschoben.

**Regressionsschutz:** Nach jeder Phase `git diff` auf die bereits committeten Nordpunkt-Outputs
(Ground-Truth-JSON, Stufe-1-Bericht, Stufe-2-Bericht) geprueft — in allen Faellen nur eine bewusste
`client_id`-Metadaten-Ergaenzung bzw. generische Formulierungen, **keine** Zahlenabweichung. Zusaetzlich
neuer, gezielter Test `tests/test_nordpunkt_ground_truth_regression.py` (Golden-Values fuer TV/Radio/
Paid_Search_Brand) als dauerhafte Absicherung — bewusste kleine Ausnahme vom bisher rein manuellen
Testvorgehen dieses Projekts.

**Alte Pfadangaben in fruoeheren Eintraegen dieses Logs** (z.B. `reports/stage_gates/
stage2_eignungsbericht.md`, `data/interim/nordpunkt_synthetic/...`) sind historisch korrekt fuer den
Stand zum jeweiligen Zeitpunkt, wurden aber durch obiges Namespacing abgeloest — aktuelle Pfade siehe
`docs/model_card.md` und `docs/datenquellen_register.md`.

---

## 2026-09-20 — Multi-Client-Generalisierung (Phasen 5-7): EDA, Streamlit-App, Doku

**Stufe 3 (EDA) und Visualisierung:** Sechs Charts (`src/visualization/charts.py`), bewusst
begrenzt: kein Kartenmaterial (synthetische Geos ohne echte Form waeren nur Dekoration), keine
volle STL-Saisonzerlegung (kein `statsmodels`-Bedarf fuer dieses Projekt), kein Dual-Achsen-Chart
fuer Spend-vs-KPI (anerkanntes Anti-Pattern, suggeriert Zusammenhang durch willkuerliche
Achsenskalierung — stattdessen beide Reihen auf 100 indexiert, eine Achse). Kollinearitaets-Heatmap
nutzt bewusst dieselbe Funktion (`data_quality/geo_normalization.py`) wie Gate 1, damit beide Zahlen
nie auseinanderlaufen koennen. Ausgabe als eigenstaendige interaktive HTML-Dateien (Plotly via CDN),
kein `kaleido`/PNG-Export noetig — spart eine native Abhaengigkeit, HTML ist fuer Stakeholder ohnehin
naeher am "richtigen" Dashboard-Gefuehl als ein statisches Bild.

**Unified Input Schema (`docs/unified_input_schema.md`):** Struktur-Pflichtspalten sind fix
(`geo`/`time`/`channel`/`spend_eur`/`impressions` bzw. `geo`/`population`), KPI-Spaltennamen sind
frei und werden beim Upload explizit ausgewaehlt, Kontrollvariablen und Reach/Frequency-Kanaele
werden aus den Daten automatisch erkannt (`control_columns`/`reach_frequency_channels = None` in
`ClientConfig`) statt vom Nutzer deklariert — haelt den Upload so komfortabel wie moeglich.

**Streamlit-App (`app/streamlit_app.py`):** Demo-Kunde waehlen oder drei CSVs hochladen, drei Tabs
(Datenuebersicht, Stufe 2, Stufe 3), reine Wiederverwendung bestehender Module — keine eigene Logik.
**Wichtiger Bugfix waehrend des Baus:** Eine fruehe Version hat fuer alle Tabs einheitlich die
bereinigten Stufe-4-Daten bevorzugt (wie `run_stage3_eda.py`) — dadurch lief Stufe 2 versehentlich auf
bereinigten statt Rohdaten und ergab fuer Nordpunkt "rot" statt des bereits committeten "gelb" (die
lineare Interpolation der fehlenden Radio-Wochen glaettet gerade den Teil, der die TV/Radio-Korrelation
kuenstlich senkt — auf bereinigten Daten stieg sie auf 0.95). Behoben: Stufe 2 liest immer Rohdaten
(entspricht ihrem Zweck, die Daten *vor* jeder Bereinigung zu bewerten), Stufe 3 bevorzugt weiterhin
bereinigte Daten falls vorhanden.

**Deploy-Absicherung:** `app/requirements.txt` bewusst schlank (streamlit/pandas/numpy/plotly) statt
des Root-`requirements.txt`, das `google-meridian`/TensorFlow enthaelt — die App importiert das nie,
haette aber einen langsamen/fehleranfaelligen Streamlit-Cloud-Build riskiert.

**Verifikation:** Kein Browser in dieser Umgebung installiert (Playwright/Chromium fehlt) — stattdessen
App-Hilfsfunktionen direkt importiert und gegen beide Demo-Kunden sowie die Upload-Vorlagen
durchlaufen lassen (inkl. des oben beschriebenen Bugfixes), zusaetzlich zweimal lokal per
`streamlit run` gestartet und per `curl` auf sauberen Start (HTTP 200, keine Traceback im Log) geprueft.
