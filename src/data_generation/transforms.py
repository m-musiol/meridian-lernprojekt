"""Wiederverwendbare Transformationen: Adstock (Carryover) und Hill-Saettigung."""

import numpy as np


def apply_adstock(exposure: np.ndarray, decay: float) -> np.ndarray:
    """Geometrischer Adstock: adstocked[t] = exposure[t] + decay * adstocked[t-1].

    Erwartet eine zeitlich sortierte 1D-Zeitreihe (eine Geo, ein Kanal).
    """
    adstocked = np.zeros_like(exposure, dtype=float)
    carry = 0.0
    for t, value in enumerate(exposure):
        carry = value + decay * carry
        adstocked[t] = carry
    return adstocked


def hill_saturation(x: np.ndarray, ec50: float, slope: float) -> np.ndarray:
    """Hill-Funktion, Wertebereich [0, 1]. `ec50` ist der Halbsaettigungspunkt."""
    x_clipped = np.clip(x, a_min=0, a_max=None)
    ec50 = max(ec50, 1e-9)
    return x_clipped**slope / (x_clipped**slope + ec50**slope)
