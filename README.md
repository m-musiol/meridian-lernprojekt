# Meridian-Lernprojekt

Privates Weiterbildungsprojekt zum Aufbau einer Marketing-Mix-Modeling-Pipeline mit
[Google Meridian](https://github.com/google/meridian) ([Entwicklerdokumentation](https://developers.google.com/meridian?hl=de)),
nachgebildet wie ein realistisches Media-Agentur-Setup.

**Wichtig:** Kein Kundenprojekt. Es werden ausschließlich synthetisch generierte oder frei zugängliche,
öffentliche Daten verwendet — nie echte Kundendaten. Haupt-Lernfall ist die fiktive Marke
**"Nordpunkt Home & Living"** (D-A-CH-Möbel-/Wohnaccessoires-Retailer, frei erfunden).

Die Pipeline ist **mehrmandantenfähig**: jeder Kunde bekommt eine eigene Config unter
`clients/<client_id>/config.py` (siehe `src/client_config.py`) statt hartcodierter Werte. Ein
zweiter, bewusst andersartiger Demo-Kunde (`clients/vivora/`, DTC-Fitness-Marke) beweist, dass
Kanalliste, Geo-Anzahl und KPI-Namen frei austauschbar sind, ohne Code zu aendern. Eigene Daten
lassen sich zudem hochladen, solange sie dem [Unified Input Schema](docs/unified_input_schema.md)
entsprechen.

## Einstieg

Das verbindliche Regelwerk für dieses Projekt (Lernziele, Arbeitsweise, Pipeline-Stufen mit Gates,
Tech-Stack, Repo-Struktur) steht in [`CLAUDE.md`](CLAUDE.md) und
[`docs/wissensbasis_pipeline.md`](docs/wissensbasis_pipeline.md).

## Setup (lokal)

Voraussetzung: Python 3.11 oder 3.12 (siehe `docs/entscheidungsprotokoll.md` zur Versionsentscheidung).

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

VS Code nutzt automatisch das Interpreter-Setup aus `.vscode/settings.json`
(`${workspaceFolder}/.venv/Scripts/python.exe`).

Pipeline-Skripte fuer einen Kunden ausfuehren (Beispiel Nordpunkt):

```powershell
python src/data_generation/generate_synthetic_data.py --client nordpunkt
python src/data_quality/run_stage2_check.py --client nordpunkt
python src/features/handle_missing_media_weeks.py --client nordpunkt
python src/eda/run_stage3_eda.py --client nordpunkt
```

`--client vivora` (oder ein eigener neuer Ordner unter `clients/`) laeuft mit denselben Skripten.

## Streamlit-Dashboard

Interaktives Multi-Client-Dashboard (Demo-Kunde waehlen oder eigene Daten hochladen, Stufe-2-Ampel
und Stufe-3-Charts):

```powershell
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

**Kostenloses Deployment (einmalig, manuell):**

1. Repo muss auf GitHub liegen (ist es bereits, privat).
2. Auf [share.streamlit.io](https://share.streamlit.io) mit dem GitHub-Account einloggen.
3. "New app" → dieses Repo/Branch waehlen, Main file path: `app/streamlit_app.py`.
4. Unter "Advanced settings" → "Requirements file path" auf `app/requirements.txt` setzen (schlankes
   Deploy-File ohne `google-meridian`/TensorFlow, siehe `app/requirements.txt`).
5. Deploy — die App ist danach unter einer `*.streamlit.app`-URL erreichbar, automatische
   Re-Deploys bei jedem Push auf den Branch.

## Struktur

Siehe `CLAUDE.md` Abschnitt 5 für die vollständige Repository-Struktur. Kurzüberblick:

- `clients/` — eine Config je Kunde (`ClientConfig`), keine hartcodierten Kanal-/KPI-Namen im Code
- `src/` — Pipeline-Module je Stufe (Datengenerierung, Datenqualität, Feature Engineering, EDA,
  Visualisierung, Modeling, ...), alle client-config-gesteuert (`--client <id>`)
- `app/` — Streamlit-Dashboard + schlankes Deploy-`requirements.txt` + Upload-Vorlagen
- `data/` — `raw/`, `interim/`, `processed/` (nicht versioniert, deterministisch reproduzierbar per Seed),
  `ground_truth/` (versioniert, für Modell-vs-Wahrheit-Vergleich)
- `docs/` — Wissensbasis, Stakeholder-Briefing, Unified Input Schema, Datenquellen-Register,
  Entscheidungsprotokoll, Model Card
- `reports/` — Gate-Reports, EDA-Charts und persona-spezifische Stakeholder-Outputs, je Kunde
- `notebooks/` — explorative/diagnostische Notebooks
- `n8n/workflows/` — exportierte n8n-Workflow-JSONs (nur wo n8n echten Mehrwert bringt)
- `tests/` — Tests je Pipeline-Modul

## Status

Fuer Nordpunkt (Haupt-Lernfall) durchlaufen: Stufe 0 (Stakeholder-Briefing), Stufe 1
(Datenbeschaffung/-generierung), Stufe 2 (Gate 1: 🟡 GELB), vorgezogene Wochen-Imputation, Stufe 3
(EDA). Zweiter Demo-Kunde Vivora belegt die Mehrmandantenfaehigkeit end-to-end. Naechster Schritt:
Stufe 4 (vollstaendiges Unified-Schema-Mapping fuer Meridian). Fortschritt und Gate-Ergebnisse siehe
`docs/entscheidungsprotokoll.md` und `reports/stage_gates/`.
