import pandas as pd

from distcluster.steps.calpha import (
    apply_position_filter,
    derive_positions_dataframe,
    parse_mutation_position,
    parse_requested_range,
)


def test_parse_mutation_position_handles_hgvs_and_plain():
    assert parse_mutation_position("C126Y") == 126
    assert parse_mutation_position("p.G7A") == 7
    assert parse_mutation_position("bad") is None


def test_parse_requested_range_normalizes_order():
    assert parse_requested_range("303-108", None, None) == (108, 303)
    assert parse_requested_range(None, 20, 10) == (10, 20)


def test_derive_positions_and_filter():
    df = pd.DataFrame({"mutation": ["A1V", "A2V", "A3V"], "ddG_Fmax": [1.0, 2.0, 3.0]})
    pos_df = derive_positions_dataframe(df, mutation_col="mutation", ddg_col="ddG_Fmax")
    filtered = apply_position_filter(pos_df, pos_min=2, pos_max=3)
    assert filtered["position"].tolist() == [2, 3]
