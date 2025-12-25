import json

import reflex as rx
from reflex_chessboard import chessboard  # или ваш импорт


class DemoState(rx.State):
    fen: str = "start"
    last_move: str = ""
    last_payload_json: str = ""
    moves: list[str] = []
    board_orientation: str = "white"
    arrows_json: str = ""
    annotations_json: str = ""

    # Normalized annotations (server-side canonical shape).
    highlights: list[dict] = []  # e.g. [{"square": "e4", "color": "yellow"}]
    arrows: list[
        dict
    ] = []  # e.g. [{"startSquare": "e2", "endSquare": "e4", "color": "#00aa00"}]

    # React-chessboard Options API derived fields.
    square_styles: dict = {}
    board_theme: str = "default"
    # Piece set:
    # - "merida": react-chessboard built-in SVG set
    # - "assets/<name>": load SVGs from app assets at /pieces/<name>/*.svg
    piece_set: str = "assets/merida"
    show_notation: bool = True
    board_size: int = 420

    def on_move(self, payload: dict):
        # payload: {from,to,piece,promotion,fen,san}
        print(
            "[DemoState.on_move] payload =",
            json.dumps(payload, ensure_ascii=False),
            flush=True,
        )
        self.fen = payload.get("fen", self.fen)
        self.last_move = (
            payload.get("san") or f"{payload.get('from')}->{payload.get('to')}"
        )
        self.last_payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
        self.moves.append(self.last_move)

    def _refresh_annotations(self):
        """Recompute derived options and pretty JSON from normalized annotations."""
        self.annotations_json = json.dumps(
            {"highlights": self.highlights, "arrows": self.arrows},
            ensure_ascii=False,
            indent=2,
        )
        # Adapt normalized highlights -> react-chessboard squareStyles (CSSProperties).
        styles: dict[str, dict] = {}
        for h in self.highlights:
            sq = h.get("square")
            if not sq:
                continue
            color = h.get("color") or "rgba(255, 255, 0, 0.35)"
            styles[str(sq)] = {"backgroundColor": color}
        self.square_styles = styles

    def reset_board(self):
        """Server -> client sync: reset the board from Python."""
        self.fen = "start"
        self.last_move = ""
        self.last_payload_json = ""
        self.moves = []
        self.highlights = []
        self.arrows = []
        self.square_styles = {}
        self.arrows_json = ""
        self.annotations_json = ""

    def set_preset_e2e4(self):
        """Server -> client sync: set a known position from Python."""
        # After 1. e4 (white pawn e2->e4), black to move.
        self.fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"

    def toggle_orientation(self):
        """Server -> client sync: flip board orientation."""
        self.board_orientation = (
            "black" if self.board_orientation == "white" else "white"
        )

    def toggle_board_theme(self):
        self.board_theme = "gray" if self.board_theme == "default" else "default"

    def toggle_piece_set(self):
        # quick toggle between built-in and assets-based merida
        self.piece_set = (
            "merida" if self.piece_set.startswith("assets/") else "assets/merida"
        )

    def set_piece_set(self, value: str):
        self.piece_set = value

    def toggle_notation(self):
        self.show_notation = not self.show_notation

    def set_board_size(self, value: str):
        try:
            n = int(value)
            self.board_size = max(240, min(900, n))
        except ValueError:
            pass

    def on_resize(self, payload: dict):
        """Keep the Board size input in sync with user mouse-resize."""
        try:
            size = int(payload.get("size"))
        except Exception:
            return
        size = max(240, min(900, size))
        if size != self.board_size:
            self.board_size = size

    def highlight_e4(self):
        """Programmatic highlight example (server -> board)."""
        self.highlights = [{"square": "e4", "color": "rgba(255, 215, 0, 0.35)"}]
        self._refresh_annotations()

    def add_arrow_e2e4(self):
        """Programmatic arrow example (server -> board)."""
        self.arrows = [{"startSquare": "e2", "endSquare": "e4", "color": "#00aa00"}]
        self._refresh_annotations()

    def clear_annotations(self):
        """Clear all annotations (server -> board)."""
        self.highlights = []
        self.arrows = []
        self._refresh_annotations()

    def on_arrows_change(self, payload: dict):
        """Receive user-drawn arrows from the board."""
        new_arrows = payload.get("arrows", []) or []
        # Avoid log/refresh spam if the payload didn't materially change.
        if new_arrows == self.arrows:
            return
        print(
            "[DemoState.on_arrows_change] payload =",
            json.dumps(payload, ensure_ascii=False),
            flush=True,
        )
        self.arrows_json = json.dumps(payload, ensure_ascii=False, indent=2)
        self.arrows = new_arrows
        self._refresh_annotations()


def index():
    return rx.vstack(
        rx.hstack(
            rx.button("Reset (server)", on_click=DemoState.reset_board),
            rx.button("Set preset: 1.e4 (server)", on_click=DemoState.set_preset_e2e4),
            rx.button("Flip board (server)", on_click=DemoState.toggle_orientation),
            rx.button("Toggle board theme", on_click=DemoState.toggle_board_theme),
            rx.button("Toggle piece set", on_click=DemoState.toggle_piece_set),
            rx.button("Toggle notation", on_click=DemoState.toggle_notation),
            rx.select(
                [
                    "assets/merida",
                    "assets/cburnett",
                    "assets/maestro",
                    "assets/pirouetti",
                    "unicode",
                    "merida",
                ],
                value=DemoState.piece_set,
                on_change=DemoState.set_piece_set,
                placeholder="piece set",
                width="260px",
            ),
            rx.hstack(
                rx.text("Board size:"),
                rx.input(
                    value=DemoState.board_size.to_string(),
                    on_change=DemoState.set_board_size,
                    width="110px",
                ),
                rx.text("px"),
                spacing="2",
                align="center",
            ),
            rx.button("Highlight e4 (server)", on_click=DemoState.highlight_e4),
            rx.button("Arrow e2→e4 (server)", on_click=DemoState.add_arrow_e2e4),
            rx.button(
                "Clear annotations (server)", on_click=DemoState.clear_annotations
            ),
            spacing="2",
            wrap="wrap",
        ),
        rx.box(
            chessboard(
                fen=DemoState.fen,
                options={
                    "allowDragging": True,
                    "boardOrientation": DemoState.board_orientation,
                    "enableClickToMove": True,
                    "allowDrawingArrows": True,
                    "boardTheme": DemoState.board_theme,
                    "pieceSet": DemoState.piece_set,
                    "piecesBaseUrl": "/pieces",
                    "showNotation": DemoState.show_notation,
                    # Demo: make board responsive to the container (so mouse resizing works).
                    "responsive": True,
                    # Programmatic annotations (server -> board)
                    "squareStyles": DemoState.square_styles,
                    "arrows": DemoState.arrows,
                    # Keep the component-provided selected/last-move highlights enabled.
                    "enableBuiltInHighlights": True,
                    # keep the PoC size sane; users can override freely
                    # (react-chessboard uses CSS sizing; width is controlled by the wrapper box)
                    # стрелки/подсветки позже можно добавить сюда же (arrows/squareStyles)
                },
                on_move=DemoState.on_move,
                on_arrows_change=DemoState.on_arrows_change,
                on_resize=DemoState.on_resize,
            ),
            # Mouse-resizable container (grab bottom-right corner).
            style={
                # Keep it square: resize only horizontally + aspect-ratio 1/1.
                # The inner board follows container size via options.responsive=True.
                "resize": "horizontal",
                "overflow": "auto",
                "border": "1px solid rgba(0,0,0,0.15)",
                "borderRadius": "8px",
                "aspectRatio": "1 / 1",
            },
            width=DemoState.board_size.to_string() + "px",
            min_width="240px",
            max_width="900px",
        ),
        rx.text(DemoState.last_move),
        rx.code(DemoState.fen, white_space="pre-wrap"),
        rx.heading("Last payload (server received)"),
        rx.code(DemoState.last_payload_json, white_space="pre-wrap"),
        rx.heading("Arrows (server received)"),
        rx.code(DemoState.arrows_json, white_space="pre-wrap"),
        rx.heading("Annotations (normalized, server)"),
        rx.code(DemoState.annotations_json, white_space="pre-wrap"),
        rx.heading("Moves"),
        rx.foreach(DemoState.moves, lambda m: rx.text(m)),
        spacing="3",
    )


app = rx.App()
app.add_page(index, route="/")
