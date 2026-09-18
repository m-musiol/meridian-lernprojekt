"""Gezielter Regressionstest: schuetzt die Nordpunkt-Ground-Truth vor stillen Zahlendrifts.

Bewusste, kleine Ausnahme vom sonst rein manuellen Testvorgehen dieses Projekts (siehe
docs/entscheidungsprotokoll.md) — deckt genau die eine Stelle ab, an der ein Refactor
(z.B. eine versehentlich verschobene rng-Ziehung) unbemerkt andere Zahlen erzeugen wuerde,
ohne dass ein manueller Blick auf den Report es zwingend auffaellt.

Ausfuehren: pytest tests/test_nordpunkt_ground_truth_regression.py -v
(erzeugt/ueberschreibt data/raw/nordpunkt_synthetic/ und data/ground_truth/nordpunkt_ground_truth.json)
"""

import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "src" / "data_generation" / "generate_synthetic_data.py"
GROUND_TRUTH = REPO_ROOT / "data" / "ground_truth" / "nordpunkt_ground_truth.json"

# Goldwerte aus einem verifizierten Lauf mit --client nordpunkt --seed 42 (siehe Kommentar oben).
EXPECTED = {
    "TV": {"realized_roi": 1.5, "adstock_decay": 0.6, "total_spend_eur": 9_954_699.48},
    "Radio": {"realized_roi": 1.1, "adstock_decay": 0.5, "total_spend_eur": 1_829_640.21},
    "Paid_Search_Brand": {"realized_roi": 4.0, "adstock_decay": 0.1, "total_spend_eur": 2_880_875.86},
}


def test_nordpunkt_ground_truth_matches_golden_values() -> None:
    subprocess.run(
        [sys.executable, str(GENERATOR), "--client", "nordpunkt", "--seed", "42"],
        cwd=REPO_ROOT, check=True, capture_output=True,
    )
    ground_truth = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))

    for channel_name, expected in EXPECTED.items():
        actual = ground_truth["channels"][channel_name]
        for field, expected_value in expected.items():
            assert actual[field] == pytest.approx(expected_value, rel=1e-6), (
                f"{channel_name}.{field}: erwartet {expected_value}, erhalten {actual[field]} — "
                "moegliche Ursache: eine rng-Ziehung wurde verschoben/entfernt/hinzugefuegt."
            )
