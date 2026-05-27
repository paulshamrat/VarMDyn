import pandas as pd

from distcluster.steps.buried import extract_buried_dataframe


def test_extract_buried_uses_class_column_when_present():
    df = pd.DataFrame(
        {
            "mutation": ["A1V", "A2V", "A3V"],
            "sasa_class": ["Buried", "Exposed", "Partially exposed"],
            "rel_sasa_pymol_%": [90, 1, 5],
        }
    )
    buried = extract_buried_dataframe(df)
    assert buried["mutation"].tolist() == ["A1V"]


def test_extract_buried_falls_back_to_threshold():
    df = pd.DataFrame({"mutation": ["A1V", "A2V", "A3V"], "rel_sasa_pymol_0to1": [0.05, 0.2, 0.1]})
    buried = extract_buried_dataframe(df, class_col="missing", buried_threshold=10.0)
    assert buried["mutation"].tolist() == ["A1V", "A3V"]
