# Datenquellen-Register

> Jede im Projekt verwendete Datenquelle wird hier vor Nutzung mit Herkunft, Lizenz und einem klaren
> `SYNTHETIC`/`PUBLIC_OPEN_DATA`-Flag erfasst (CLAUDE.md Abschnitt 2, Punkt 4). Es darf zu keinem Zeitpunkt
> der Eindruck realer Kundendaten entstehen.

| Quelle | Herkunft | Lizenz | Flag | Zweck | Aufgenommen am |
|---|---|---|---|---|---|
| `geo_all_channels.csv` (Meridian-Simulationsdaten, Datenquelle 1) | [google/meridian](https://github.com/google/meridian), Pfad `meridian/data/simulated_data/csv/geo_all_channels.csv`, gepinnt auf Commit `00134ea24a0f811a41ee640e89c68ed884fef0ad` (2026-09-10). Lokal unter `data/raw/meridian_sample/geo_all_channels.csv`, SHA256 `d9ee016f7cd21f5c90b50da10a794af91a372b69f881d3caa266edd41fdafbf6` | Apache-2.0 | SYNTHETIC (öffentlich von Google bereitgestellt) | Modell-Mechanik verstehen / Parameter Recovery — bekannte Generatorwahrheit, erste Trainingsläufe (Stufen 5-8). Struktur: 40 Geos, 156 Wochen (2021-01-25 bis 2024-01-15), 5 Paid-Media-Kanäle (Impression+Spend), 1 Organic-Kanal, 2 Controls, Promo-Flag, KPI `conversions`/`revenue_per_conversion`, `population`. Keine Reach/Frequency-Daten enthalten (dafür ggf. `geo_media_rf.csv` separat nachladen). | 2026-09-13 |
