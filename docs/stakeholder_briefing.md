# Stakeholder-Briefing — Nordpunkt Home & Living

> Stufe 0 (Auftragsklärung) gemäß `docs/wissensbasis_pipeline.md` Abschnitt 2. Fiktiver Agentur-Kickoff für
> die frei erfundene Marke **"Nordpunkt Home & Living"**. Alle mit **[ANNAHME]** markierten Angaben sind
> plausible Setzungen für den Lernzweck, keine realen Werte — sie werden vor Stufe 1 final abgestimmt.

---

## 1. Kontext (Annahme)

**[ANNAHME]** Nordpunkt Home & Living ist ein D-A-CH-Möbel- und Wohnaccessoires-Retailer mit Online-Shop
und einem Filialnetz (mittlere Größenordnung, ca. 40-60 Filialen, Schwerpunkt Deutschland). Hauptsaison:
Q1 (Neujahrs-/Einrichtungsimpuls) und Q4 (Weihnachtsgeschäft/Möbelaktionen). Wettbewerbsintensives Umfeld
mit hoher Preistransparenz (Vergleichsportale).

## 2. Business-Fragen

1. Welchen inkrementellen Beitrag leistet jeder Media-Kanal zu Abverkauf/Revenue und zu Website-Sessions?
2. Ab welchem Spend-Niveau sättigt sich der Effekt je Kanal (abnehmende Grenzerträge)?
3. Wie lange wirkt eine Kampagne nach (Adstock/Carryover) — lohnt sich ein TV-Flight vor dem Q4-Peak?
4. Wie sollte das Budget über Kanäle (und ggf. Zeit) alloziert werden, um Umsatz bei gegebenem Budget zu
   maximieren?
5. Wie unterscheiden sich Regionen in ihrer Media-Reaktion (falls Geo-Modell umsetzbar, siehe Gate 1)?
6. Wie groß ist der Effekt von Preis, Promotions und Saisonalität im Vergleich zu Media — wird Media
   überschätzt, wenn diese Störgrößen fehlen?

## 3. Ziel-KPIs

| KPI | Rolle | Ebene |
|---|---|---|
| **Abverkauf/Revenue (€)** | Primäre Zielgröße | wöchentlich, je Geo |
| **Website-Sessions** | Sekundäre Zielgröße | wöchentlich, je Geo |

**Offene Entscheidung (wird in Stufe 5/Decision Log final getroffen):** Sessions als eigenständiges zweites
Meridian-Modell ODER als Mediator/Funnel-Stufe vor Revenue in einem Full-Funnel-Setup. **[ANNAHME für den
Start]:** zwei separate Modelle — einfacher zu interpretieren für den Lernzweck, Full-Funnel als mögliche
Erweiterung später.

## 4. Kanäle (Annahme, gemäß Datenstrategie)

**Paid Media:** TV, Video/YouTube, Programmatic Display, Paid Social, Paid Search Brand, Paid Search
Non-Brand, Affiliate, Out-of-Home, Radio (mind. TV und Paid Social mit Reach/Frequency-Daten).
**Organic Media:** organische Suchklicks/Impressions, Social-Organic-Reichweite.
**Non-Media Treatments:** Distributions-/Filialanzahl, Sortimentsbreite.
**Controls:** Preisindex, Promotion-Flag, Saisonalität/Feiertage, Wetter (Temperatur), Konsumklima-Proxy,
Wettbewerber-Spend-Proxy.

## 5. Budgetrahmen (Annahme)

**[ANNAHME]** Jährliches Media-Gesamtbudget ca. **8-12 Mio. €** für den DACH-Markt, Schwerpunkt Deutschland.
Kanal-Split grob: TV ~30 %, Programmatic/Display ~15 %, Paid Social ~15 %, Paid Search (Brand+Non-Brand)
~20 %, restliche Kanäle (Affiliate, OOH, Radio, Video) ~20 %. Dieser Split dient nur als Ausgangspunkt für
die synthetische Datengenerierung in Stufe 1.

## 6. Zeitraum & Granularität

**156 Wochen (3 Jahre) historisch**, wöchentliche Granularität, Geo-Ebene: **[ANNAHME]** vereinfachte
Struktur mit 8-12 Geo-Einheiten (z.B. zusammengefasste deutsche Bundesländer-Cluster) — finale Geo-Zahl wird
in Stufe 1 anhand der Heuristik "Geos × Zeitpunkte vs. Parameterzahl" (Gate 1) geprüft.

## 7. Reporting-Kadenz (Annahme)

**[ANNAHME]** Monatliches Kurz-Update an Geschäftsführung/Finance (Ampel-Status, keine Modelländerung),
vollständiges Modell-Update inkl. neuer Diagnostik quartalsweise. Für dieses Lernprojekt: nach jedem
abgeschlossenen Pipeline-Durchlauf (Stufe 11).

## 8. Erfolgskriterien

- **Modellgüte:** R-hat < 1.05, keine Divergences, Holdout-MAPE in einem für MMM üblichen Korridor
  (Richtwert, kein Hard-Cutoff — wird in Stufe 7 kalibriert).
- **Business-Plausibilität:** ROI-Werte je Kanal liegen in einem nachvollziehbaren Korridor; bei
  synthetischen Daten zusätzlich Abgleich Modell-Schätzung vs. `ground_truth`.
- **Kommunizierbarkeit:** Ergebnis lässt sich der Geschäftsführung in 3 Sätzen mit konkreter
  Handlungsempfehlung zusammenfassen (Stufe 11).
- **Lernziel-Erfüllung:** alle in `CLAUDE.md` Abschnitt 1 genannten Stellschrauben wurden mindestens einmal
  bewusst variiert und ihre Wirkung beobachtet/dokumentiert.

---

*Alle Annahmen in diesem Dokument sind Ausgangspunkte für die synthetische Datengenerierung (Stufe 1) und
können dort noch angepasst werden — nichts hiervon bildet eine reale Marke oder reale Zahlen ab.*
