import pytest

from reflex_chess_model import validate_tree


def test_validate_tree_accepts_minimal_valid_tree():
    tree = {
        "version": 1,
        "headers": {},
        "initialFen": "start",
        "rootId": "n:root",
        "nodes": {
            "n:root": {
                "id": "n:root",
                "ply": 0,
                "fen": "start",
                "parent": None,
                "children": [],
            }
        },
        "moveByNode": {},
        "nodeByFen": {"start": ["n:root"]},
        "mainline": ["n:root"],
        "nextMainline": {"n:root": None},
        "prevMainline": {"n:root": None},
    }
    validate_tree(tree)


def test_validate_tree_rejects_wrong_version():
    with pytest.raises(ValueError, match="PackedGameTree\\.version"):
        validate_tree({"version": 2})


