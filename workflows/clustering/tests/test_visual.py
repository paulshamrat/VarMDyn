import pandas as pd

from distcluster.steps.visual import color_map_by_leaf_order, order_by_cluster, parse_color_list


def test_color_map_follows_leftmost_leaf_order():
    leaf_positions = [20, 30, 10, 40]
    assign = pd.DataFrame({"position": [10, 20, 30, 40], "cluster": [2, 1, 1, 2]})
    cmap, ordered = color_map_by_leaf_order(leaf_positions, assign, ["#a", "#b"])
    assert ordered == [1, 2]
    assert cmap[1] == "#a"
    assert cmap[2] == "#b"


def test_order_by_cluster_returns_blocks():
    labels = [10, 20, 30, 40]
    assign = pd.DataFrame({"position": [30, 10, 20], "cluster": [2, 1, 1]})
    idx, blocks = order_by_cluster(assign, labels)
    assert idx == [0, 1, 2]
    assert blocks == [(1, 0, 1), (2, 2, 2)]


def test_parse_color_list_accepts_yaml_list():
    cols = parse_color_list(["#2ca02c", "#ff7f0e", "#9467bd"])
    assert cols == ["#2ca02c", "#ff7f0e", "#9467bd"]
