from reflex_chess_viewer import GameTreeBuilder


def test_builder_builds_minimal_tree():
    pgn = """[Event "Demo"]

1. e4 (1. d4 d5) e5 *
"""
    tree = GameTreeBuilder().build(pgn)
    assert tree["version"] == 1
    assert tree["rootId"] == "n:root"
    assert "n:0" in tree["nodes"]
    assert tree["nodes"]["n:root"]["children"][0] == "n:0"
    assert "n:0" in tree["moveByNode"]
    assert tree["mainline"][0] == "n:root"


