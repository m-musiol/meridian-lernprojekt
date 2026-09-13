# Meridian-Lernprojekt

Privates Weiterbildungsprojekt zum Aufbau einer Marketing-Mix-Modeling-Pipeline mit
[Google Meridian](https://github.com/google/meridian) ([Entwicklerdokumentation](https://developers.google.com/meridian?hl=de)),
nachgebildet wie ein realistisches Media-Agentur-Setup.

**Wichtig:** Kein Kundenprojekt. Es werden ausschließlich synthetisch generierte oder frei zugängliche,
öffentliche Daten verwendet — nie echte Kundendaten. Fiktive Marke: **"Nordpunkt Home & Living"**
(D-A-CH-Möbel-/Wohnaccessoires-Retailer, frei erfunden).

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

## Struktur

Siehe `CLAUDE.md` Abschnitt 5 für die vollständige Repository-Struktur. Kurzüberblick:

- `src/` — Pipeline-Module je Stufe (Datengenerierung, Datenqualität, Feature Engineering, Modeling, ...)
- `data/` — `raw/`, `interim/`, `processed/` (nicht versioniert, deterministisch reproduzierbar per Seed),
  `ground_truth/` (versioniert, für Modell-vs-Wahrheit-Vergleich)
- `docs/` — Wissensbasis, Stakeholder-Briefing, Datenquellen-Register, Entscheidungsprotokoll, Model Card
- `reports/` — Gate-Reports und persona-spezifische Stakeholder-Outputs
- `notebooks/` — explorative/diagnostische Notebooks
- `n8n/workflows/` — exportierte n8n-Workflow-JSONs (nur wo n8n echten Mehrwert bringt)
- `tests/` — Tests je Pipeline-Modul

## Status

Projekt befindet sich in Stufe 0 (Auftragsklärung & Stakeholder-Briefing). Fortschritt und Gate-Ergebnisse
siehe `docs/entscheidungsprotokoll.md` und `reports/stage_gates/`.
