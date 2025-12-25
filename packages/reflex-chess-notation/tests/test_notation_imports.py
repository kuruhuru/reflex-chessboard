import os


def test_package_imports_and_component_contract():
    os.environ["REFLEX_BACKEND_ONLY"] = "1"

    from reflex_chess_notation import chess_notation

    assert callable(chess_notation)


