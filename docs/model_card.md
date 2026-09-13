# Model Card — Meridian-Lernprojekt

> Wird nach jedem Trainingslauf aktualisiert (CLAUDE.md Abschnitt 2, Punkt 6). Noch kein Modell trainiert.

## Aktuelle Datenversion

_(folgt in Stufe 4/5)_

## Priors

_(folgt in Stufe 5)_

## Diagnosewerte

| Lauf | Datum | R-hat | ESS | Divergences | Holdout RMSE/MAPE | Settings (Chains/Draws) | Hardware |
|---|---|---|---|---|---|---|---|
| _(noch kein Lauf)_ | | | | | | | |

## Bekannte Limitierungen

- **Fehlende Wochen bei Out_of_Home und Radio (~5,1 %):** Aus Stufe 2 (Gate 1, 🟡 GELB), siehe
  `reports/stage_gates/stage2_eignungsbericht.md`. Bewusst in den Generator eingebaute Meldeluecken
  (`data/raw/nordpunkt_synthetic/media.csv`, `spend_eur`/`impressions` = `NaN`). Muss vor Stufe 4
  explizit behandelt werden (Interpolation oder Null-Fill mit Flag), sonst NaN-Propagation ins
  Input-Array-Mapping.
- **Moderate TV↔Radio-Kollinearitaet (r≈0,59, VIF≈2,2 auf Geo-Wochen-Ebene pro Kopf):** bewusst
  eingebaut (siehe `datenquellen_register.md`), Check faellt noch gruen aus, aber im Auge behalten —
  bei Prior-Wahl in Stufe 5 ggf. engere/informativere Priors fuer TV und Radio in Erwaegung ziehen,
  falls sich die Effekte in der Diagnostik (Stufe 7) nicht sauber trennen lassen.
