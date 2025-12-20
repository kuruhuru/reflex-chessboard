import os


def test_package_imports_and_component_contract():
    # Avoid creating symlinks into an app assets folder during import-time smoke tests.
    os.environ["REFLEX_BACKEND_ONLY"] = "1"

    import reflex_chessboard  # noqa: F401
    from reflex_chessboard import Chessboard, chessboard

    assert callable(chessboard)
    assert Chessboard.tag == "ReflexChessboardShim"
    # `library` is intentionally not used: the shim is injected via `_get_custom_code`
    # and loaded client-side to avoid Vite importing `.jsx` from `/public`.
    assert any(dep.startswith("react-chessboard@") for dep in Chessboard.lib_dependencies)
    assert any(dep.startswith("chess.js@") for dep in Chessboard.lib_dependencies)

    # Ensure custom JS shim code exists.
    inst = Chessboard.create()
    assert "const ReflexChessboardShim = ClientSide" in (inst._get_custom_code() or "")


