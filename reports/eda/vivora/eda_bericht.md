# Stufe 3 — EDA-Bericht (Vivora Sport & Fitness)

Datenbasis: Rohdaten (Stufe 4 noch nicht gelaufen).

Alle Charts sind interaktiv (Hover fuer Werte, Zoom, Legende an-/abschaltbar) — als eigenstaendige HTML-Dateien in diesem Ordner, keine Bilddateien.

## KPI-Trend ueber Zeit

[`kpi_trend.html`](kpi_trend.html)

Zeigt Wachstum, Rueckgaenge und grobe Saisonmuster der Zielgroessen auf einen Blick — der erste Chart, den ein Stakeholder normalerweise sehen will.

## Spend-Share nach Kanal

[`spend_share.html`](spend_share.html)

Zeigt, wie sich der Media-Mix ueber die Zeit verschiebt (z.B. saisonale Umschichtungen) — Balken statt eines einzelnen Kreisdiagramms, weil sich der Mix ueber ein Jahr veraendert, nicht statisch ist.

## Spend vs. KPI (indexiert)

[`spend_vs_kpi.html`](spend_vs_kpi.html)

Beide Linien auf 100 = erste Woche indexiert und auf einer Achse dargestellt (bewusst kein Dual-Achsen-Chart, der durch willkuerliche Skalierung einen Zusammenhang vortaeuschen koennte). Zeigt nur grobe Ko-Bewegung — keine kausale Aussage, dafuer ist Stufe 5-8 (das eigentliche Modell) da.

## Saisonalitaet

[`seasonality.html`](seasonality.html)

Kalenderwochen der einzelnen Jahre uebereinandergelegt — zeigt, ob sich wiederkehrende Muster (z.B. Q4-Peak) Jahr fuer Jahr aehnlich zeigen.

## Kanal-Korrelations-Heatmap

[`correlation_heatmap.html`](correlation_heatmap.html)

Identische Berechnung wie der Stufe-2-Kollinearitaets-Check (pro Kopf, Geo-Wochen-Ebene) — visualisiert, welche Kanalpaare sich schwer trennen lassen werden.

## Geo-Level-Variation

[`geo_variation.html`](geo_variation.html)

Durchschnittliche KPI pro Kopf je Geo, sortiert. Keine Kartendarstellung: die synthetischen Geos (`Region_01` ...) haben keine echten Geoformen, eine Karte waere hier nur Dekoration.
