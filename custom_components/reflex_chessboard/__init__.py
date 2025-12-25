from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from .chessboard import Chessboard, chessboard

__all__ = [
    "Chessboard",
    "chessboard",
    "builtin_pieces_base_url",
    "builtin_piece_options",
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


def builtin_piece_options(set_name: str) -> dict[str, str]:
    """Convenience helper to build `options` for a built-in piece set.

    Example:
        options = {
            **builtin_piece_options("merida"),
            "allowDragging": True,
        }
    """
    return {
        "pieceSet": f"assets/{set_name}",
        "piecesBaseUrl": builtin_pieces_base_url(),
    }


def register_builtin_piece_assets(sets: Iterable[str] | None = None) -> None:
    """Expose built-in piece SVGs as shared assets for the current Reflex app.

    Call this at app import/compile time (e.g., in your app module or `rxconfig.py`)
    if you want to use built-in sets via:
      - options: { "pieceSet": "assets/<name>", "piecesBaseUrl": builtin_pieces_base_url() }
    """
    from importlib import resources

    import reflex as rx

    backend_only = os.environ.get("REFLEX_BACKEND_ONLY") == "1"
    if backend_only:
        # No frontend compilation; nothing to symlink.
        return

    available = set(list_builtin_piece_sets())
    if sets is None:
        wanted = set(available)
    else:
        wanted = set(sets)
        unknown = sorted(wanted - available)
        if unknown:
            msg = (
                "Unknown built-in piece set(s): "
                + ", ".join(unknown)
                + ". Available: "
                + ", ".join(sorted(available))
            )
            raise ValueError(msg)

    if not wanted:
        return

    # Ensure the destination external assets directory exists.
    # This avoids confusing errors in some integration setups where the app's
    # assets folder hasn't been initialized yet.
    dest_root = Path.cwd() / "assets" / "external" / "reflex_chessboard" / "pieces"
    dest_root.mkdir(parents=True, exist_ok=True)

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
            try:
                rx.asset(f"pieces/{set_name}/{svg.name}", shared=True)
            except FileNotFoundError as e:
                # Most common cause: user installed an older wheel without SVG package-data.
                raise FileNotFoundError(
                    "Built-in piece assets were not found on disk. "
                    "Make sure you're using a version of `reflex-chessboard` that ships "
                    "SVG assets, or reinstall/upgrade the package. "
                    f"Missing file: {e}"
                ) from e