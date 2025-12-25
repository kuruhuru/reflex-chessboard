from __future__ import annotations

from collections.abc import Iterable

from .chessboard import Chessboard, chessboard

__all__ = [
    "Chessboard",
    "chessboard",
    "builtin_pieces_base_url",
    "list_builtin_piece_sets",
    "register_builtin_piece_assets",
]


def builtin_pieces_base_url() -> str:
    """Base URL for built-in SVG piece assets shipped with this package.

    These assets are exposed via Reflex shared assets at:
    `/external/reflex_chessboard/pieces/...`
    """
    # Keep in sync with Reflex's shared-asset URL scheme and module name.
    return "/external/reflex_chessboard/pieces"


def list_builtin_piece_sets() -> list[str]:
    """List built-in piece set names shipped with the package."""
    from importlib import resources

    pieces = resources.files("reflex_chessboard").joinpath("pieces")
    if not pieces.is_dir():
        return []
    return sorted([p.name for p in pieces.iterdir() if p.is_dir()])


def register_builtin_piece_assets(sets: Iterable[str] | None = None) -> None:
    """Expose built-in piece SVGs as shared assets for the current Reflex app.

    Call this at app import/compile time (e.g., in your app module or `rxconfig.py`)
    if you want to use built-in sets via:
      - options: { "pieceSet": "assets/<name>", "piecesBaseUrl": builtin_pieces_base_url() }
    """
    import os
    from importlib import resources

    import reflex as rx

    backend_only = os.environ.get("REFLEX_BACKEND_ONLY") == "1"
    if backend_only:
        # No frontend compilation; nothing to symlink.
        return

    available = set(list_builtin_piece_sets())
    wanted = set(sets) if sets is not None else available
    wanted = wanted & available

    if not wanted:
        return

    pieces_dir = resources.files("reflex_chessboard").joinpath("pieces")
    for set_name in sorted(wanted):
        set_dir = pieces_dir.joinpath(set_name)
        if not set_dir.is_dir():
            continue
        for svg in sorted(set_dir.iterdir()):
            if not svg.is_file() or not svg.name.lower().endswith(".svg"):
                continue
            # Use shared assets. `path` is relative to this __init__.py directory,
            # so it must match the on-disk layout in the installed package.
            rx.asset(f"pieces/{set_name}/{svg.name}", shared=True)