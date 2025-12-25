import os
from pathlib import Path

import reflex as rx

# Cleanup legacy/broken symlinks under assets/external (leftovers from an earlier
# PoC that used rx.asset(..., shared=True) for the JSX shim). Broken symlinks can
# trigger continuous reload loops in dev mode.
_assets_external = Path(__file__).resolve().parent / "assets" / "external"
if _assets_external.exists():
    for p in _assets_external.rglob("*"):
        try:
            if p.is_symlink() and not p.exists():
                p.unlink(missing_ok=True)
        except OSError:
            # Best-effort cleanup; ignore permission and transient FS errors.
            pass


# Avoid hot-reload loops on some environments (notably WSL2) where the frontend build
# continuously writes into `.web/` and triggers backend reloads.
#
# Reflex reads these as colon-separated absolute paths.
_app_root = Path(__file__).resolve().parent
_default_excludes = [
    _app_root / ".web",
    _app_root / ".react-router",
    _app_root / "dist",
    _app_root / "build",
]
_exclude_env = os.environ.get("REFLEX_HOT_RELOAD_EXCLUDE_PATHS", "")
if not _exclude_env:
    os.environ["REFLEX_HOT_RELOAD_EXCLUDE_PATHS"] = ":".join(
        str(p) for p in _default_excludes if p.exists()
    )

# Include the monorepo component source for hot-reload while developing the demo.
# Otherwise, changes under `packages/*` won't trigger a recompile.
_repo_root = _app_root.parent.parent
_default_includes = [
    _repo_root / "packages" / "reflex-chessboard" / "custom_components",
    _repo_root / "packages" / "reflex-chess-model" / "src",
    _repo_root / "packages" / "reflex-chess-notation" / "src",
    _repo_root / "packages" / "reflex-chess-viewer" / "src",
]
_include_env = os.environ.get("REFLEX_HOT_RELOAD_INCLUDE_PATHS", "")
if not _include_env:
    os.environ["REFLEX_HOT_RELOAD_INCLUDE_PATHS"] = ":".join(
        str(p) for p in _default_includes if p.exists()
    )

config = rx.Config(
    app_name="demo_pgn_viewer",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
)
