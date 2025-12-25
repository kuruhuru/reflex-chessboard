from __future__ import annotations

from typing import Any

import reflex as rx

from reflex_chess_model import validate_tree
from reflex_chess_notation import NotationLine, build_notation_lines, chess_notation
from reflex_chessboard import chessboard

from .builder import GameTreeBuilder
from .projection import project_shapes_to_board_options


UPLOAD_ID = "pgn-upload"


class ChessViewerState(rx.State):
    pgn_error: str = ""
    selected_id: str = "n:root"
    fen: str = "start"

    tree: dict = {}
    notation_lines: list[NotationLine] = []

    # Optional: user overrides for board/notation (MVP: minimal).
    board_options: dict[str, Any] = {}
    board_options_effective: dict[str, Any] = {}
    notation_options: dict[str, Any] = {
        "show_move_numbers": True,
        "show_comments": True,
        "show_nags": True,
        "unknown_nag_mode": "hide",
        "max_variation_depth": 8,
    }

    def _recompute_effective_board_options(self) -> None:
        base: dict[str, Any] = dict(self.board_options or {})

        shapes: list[dict[str, Any]] = []
        try:
            root_id = str(self.tree.get("rootId") or "n:root")
            if self.selected_id and self.selected_id != root_id:
                mbn = self.tree.get("moveByNode") or {}
                mi = mbn.get(self.selected_id) if isinstance(mbn, dict) else None
                ann = mi.get("annotations") if isinstance(mi, dict) else None
                shapes = ann.get("shapes") if isinstance(ann, dict) else []
        except Exception:
            shapes = []

        proj = project_shapes_to_board_options(shapes or [])

        # squareStyles: viewer wins on conflicts
        user_square = base.get("squareStyles") or {}
        viewer_square = proj.get("squareStyles") or {}
        if isinstance(user_square, dict) and isinstance(viewer_square, dict):
            base["squareStyles"] = {**user_square, **viewer_square}
        else:
            base["squareStyles"] = viewer_square

        # arrows: merge user + viewer
        user_arrows = base.get("arrows") or []
        viewer_arrows = proj.get("arrows") or []
        if isinstance(user_arrows, list) and isinstance(viewer_arrows, list):
            base["arrows"] = [*user_arrows, *viewer_arrows]
        else:
            base["arrows"] = viewer_arrows

        self.board_options_effective = base

    def _set_from_tree_root(self) -> None:
        root_id = str(self.tree.get("rootId") or "n:root")
        self.selected_id = root_id
        self.fen = str(self.tree.get("initialFen") or "start")
        self._recompute_effective_board_options()

    def load_pgn_text(self, pgn: str) -> None:
        self.pgn_error = ""
        try:
            tree = GameTreeBuilder().build(pgn)
            validate_tree(tree)
        except Exception as e:
            self.tree = {}
            self.notation_lines = []
            self.selected_id = "n:root"
            self.fen = "start"
            self.board_options_effective = {}
            self.pgn_error = str(e)
            return

        self.tree = tree
        self._set_from_tree_root()
        self.notation_lines = build_notation_lines(tree, options=self.notation_options)

    def on_select(self, payload: dict) -> None:
        node_id = payload.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            return
        if not self.tree:
            return
        nodes = self.tree.get("nodes") or {}
        node = nodes.get(node_id) if isinstance(nodes, dict) else None
        if not isinstance(node, dict):
            return
        self.selected_id = node_id
        self.fen = str(node.get("fen") or self.fen)
        self._recompute_effective_board_options()

    def nav_start(self) -> None:
        if not self.tree:
            return
        self._set_from_tree_root()

    def nav_end(self) -> None:
        if not self.tree:
            return
        ml = self.tree.get("mainline") or []
        if isinstance(ml, list) and ml:
            self.on_select({"node_id": ml[-1]})

    def nav_back(self) -> None:
        if not self.tree:
            return
        prev = (self.tree.get("prevMainline") or {}).get(self.selected_id)
        if isinstance(prev, str) and prev:
            self.on_select({"node_id": prev})

    def nav_forward(self) -> None:
        if not self.tree:
            return
        nxt = (self.tree.get("nextMainline") or {}).get(self.selected_id)
        if isinstance(nxt, str) and nxt:
            self.on_select({"node_id": nxt})

    def on_pgn_upload(self, files: list[rx.UploadFile]) -> None:
        # Read the first uploaded file and parse it as PGN.
        if not files:
            return
        f = files[0]
        try:
            raw = f.file.read()
            text = raw.decode("utf-8", errors="replace")
        except Exception as e:
            self.pgn_error = f"upload read failed: {e}"
            return
        self.load_pgn_text(text)

    def ignore_move(self, payload: dict) -> None:  # noqa: ARG002
        # Viewer is read-only on MVP: ignore board input.
        return


def chess_viewer() -> rx.Component:
    upload = rx.upload.root(
        rx.vstack(
            rx.text("Drop PGN here or click to choose a file (.pgn)"),
            rx.text("После выбора файл будет прочитан на сервере и распарсен через python-chess.", opacity="0.75", font_size="12px"),
            spacing="1",
        ),
        id=UPLOAD_ID,
        multiple=False,
        max_files=1,
        accept={"text/plain": [".pgn", ".txt"]},
        border="1px dashed rgba(0,0,0,0.25)",
        border_radius="10px",
        padding="12px",
        width="100%",
        on_drop=ChessViewerState.on_pgn_upload,
    )

    toolbar = rx.hstack(
        rx.button("Start", on_click=ChessViewerState.nav_start),
        rx.button("Back", on_click=ChessViewerState.nav_back),
        rx.button("Forward", on_click=ChessViewerState.nav_forward),
        rx.button("End", on_click=ChessViewerState.nav_end),
        spacing="2",
        wrap="wrap",
    )

    main = rx.hstack(
        rx.box(
            chessboard(
                fen=ChessViewerState.fen,
                options=ChessViewerState.board_options_effective,
                on_move=ChessViewerState.ignore_move,  # read-only MVP
            ),
            width="480px",
            max_width="100%",
        ),
        rx.box(
            chess_notation(
                lines=ChessViewerState.notation_lines,
                selected_id=ChessViewerState.selected_id,
                on_select=ChessViewerState.on_select,
            ),
            width="100%",
        ),
        spacing="4",
        align="start",
        wrap="wrap",
    )

    debug = rx.vstack(
        rx.hstack(rx.text("selected_id:"), rx.code(ChessViewerState.selected_id), spacing="2"),
        rx.hstack(rx.text("fen:"), rx.code(ChessViewerState.fen), spacing="2"),
        spacing="1",
    )

    return rx.vstack(
        upload,
        rx.cond(ChessViewerState.pgn_error != "", rx.callout(ChessViewerState.pgn_error, color_scheme="red")),
        toolbar,
        main,
        debug,
        spacing="4",
        width="100%",
    )


