"""Synthetic numerical checks independent of private trajectories."""

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ENTROPY = (
    ROOT
    / "scripts/analysis/05_entropy/02_fullcore13_297/03_windows/02_last400ns_100_500"
)


def load(name):
    spec = importlib.util.spec_from_file_location("entropy_test_module", ENTROPY / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_entropy_localized_and_uniform():
    module = load("analyze-sidechain-entropy-fast.py")
    assert np.isclose(module.entropy_counts(np.array([100, 0, 0]))[0], 0)
    assert np.isclose(module.entropy_counts(np.ones(9))[0], np.log(9))


def test_rotamer_periodicity():
    module = load("build-rotamer-states.py")
    angles = np.array([-179.0, -60.0, 60.0, 179.0])
    assert np.array_equal(module.chi1_state(angles), module.chi1_state(angles + 360))
