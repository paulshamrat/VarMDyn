import pandas as pd

from distcluster.steps.merge_sasa import merge_sasa_dataframe, parse_mutation_position


def test_parse_mutation_position():
    assert parse_mutation_position("C126Y") == 126
    assert parse_mutation_position("  G7A ") == 7
    assert parse_mutation_position("bad") is None


def test_merge_sasa_dataframe_maps_positions():
    ddg = pd.DataFrame({"mutation": ["A1V", "C2Y", "Z9Q"], "ddG_Fmax": [1.0, 2.0, 3.0]})
    sasa = pd.DataFrame(
        {
            "pymol_chain": ["A", "A"],
            "pymol_res3": ["MET", "LYS"],
            "pos": [1, 2],
            "rel_sasa_pymol_0to1": [0.91, 0.12],
            "rel_sasa_pymol_%": [91, 12],
        }
    )

    merged = merge_sasa_dataframe(ddg, sasa, mutation_col="mutation")
    assert merged["rel_sasa_pymol_%"].iloc[0] == 91
    assert merged["rel_sasa_pymol_%"].iloc[1] == 12
    assert pd.isna(merged["rel_sasa_pymol_%"].iloc[2])
