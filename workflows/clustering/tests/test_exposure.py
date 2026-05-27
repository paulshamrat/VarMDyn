import pandas as pd

from distcluster.steps.exposure import classify_exposure_dataframe, exposure_class


def test_exposure_class_boundaries():
    assert exposure_class(10.0, 10.0, 50.0) == "Buried"
    assert exposure_class(10.1, 10.0, 50.0) == "Partially exposed"
    assert exposure_class(50.0, 10.0, 50.0) == "Partially exposed"
    assert exposure_class(50.1, 10.0, 50.0) == "Exposed"


def test_classify_dataframe_from_rel01_column():
    df = pd.DataFrame({"mutation": ["A1V", "A2V", "A3V"], "rel_sasa_pymol_0to1": [0.05, 0.2, 0.8]})
    out = classify_exposure_dataframe(df, buried_threshold=10.0, exposed_threshold=50.0)
    assert out["rel_sasa_used_%"].tolist() == [5.0, 20.0, 80.0]
    assert out["sasa_class"].tolist() == ["Buried", "Partially exposed", "Exposed"]
