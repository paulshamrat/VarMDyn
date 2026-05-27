import pandas as pd

from distcluster.steps.exposureplot import build_exposure_palette, classify_rel_sasa, pick_rel_sasa_01


def test_pick_rel_sasa_prefers_rel01_column():
    df = pd.DataFrame({"rel_sasa_pymol_0to1": [0.1, 0.2]})
    s = pick_rel_sasa_01(df)
    assert s.tolist() == [0.1, 0.2]


def test_classify_rel_sasa_boundaries():
    rel = pd.Series([0.05, 0.10, 0.20, 0.40, 0.8])
    cls = classify_rel_sasa(rel, buried_thr=0.10, exposed_thr=0.40)
    assert cls.tolist() == ["Buried", "Buried", "Partially exposed", "Exposed", "Exposed"]


def test_build_exposure_palette_accepts_yaml_list():
    pal = build_exposure_palette(["#FFD700", "#1F4E79", "#A8A8A8"])
    assert pal["Buried"] == "#FFD700"
    assert pal["Partially exposed"] == "#1F4E79"
    assert pal["Exposed"] == "#A8A8A8"
