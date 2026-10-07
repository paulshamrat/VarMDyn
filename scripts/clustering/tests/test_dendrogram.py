import numpy as np

from distcluster.steps.dendrogram import parse_color_list, threshold_for_k


def test_parse_color_list_defaults_when_empty():
    colors = parse_color_list(None)
    assert len(colors) >= 3


def test_parse_color_list_splits_csv():
    assert parse_color_list("#111,#222") == ["#111", "#222"]


def test_threshold_for_k_intermediate():
    # fake linkage distances increasing: 1.0, 2.0, 3.0 for N=4
    z = np.array(
        [
            [0, 1, 1.0, 2],
            [2, 3, 2.0, 2],
            [4, 5, 3.0, 4],
        ],
        dtype=float,
    )
    t = threshold_for_k(z, k=2, n_leaves=4)
    assert 2.0 <= t <= 3.0
