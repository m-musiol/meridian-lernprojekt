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

**Befund:** `C:\Users\marcm\datascience\DS` ist selbst die Wurzel eines bestehenden Git-Repos (Remote
`git@github.com:m-musiol/reddit_stock_analyzer.git`), das alle Projektunterordner enthält. Dessen
`.gitignore` schließt jedoch pauschal alles außer `/reddy/` aus — `meridian-lernprojekt/` wird von diesem
äußeren Repo also nicht getrackt.

**Entscheidung:** `meridian-lernprojekt/` erhält ein eigenständiges, neu initialisiertes Git-Repo
(`git init` in diesem Ordner) und ein eigenes GitHub-Repo (`gh repo create`, privat), unabhängig vom
äußeren `DS`-Repo und von `reddit_stock_analyzer`. So bleibt dieses Lernprojekt sauber von anderen,
unabhängigen Projekten (Trading-/Reddit-Analyse) getrennt.

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
