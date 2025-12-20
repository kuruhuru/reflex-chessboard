import reflex as rx
from reflex_chessboard import chessboard  # или ваш импорт
import json


class DemoState(rx.State):
    fen: str = "start"
    last_move: str = ""
    last_payload_json: str = ""
    moves: list[str] = []
    board_orientation: str = "white"

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

    def reset_board(self):
        """Server -> client sync: reset the board from Python."""
        self.fen = "start"
        self.last_move = ""
        self.last_payload_json = ""
        self.moves = []

    def set_preset_e2e4(self):
        """Server -> client sync: set a known position from Python."""
        # After 1. e4 (white pawn e2->e4), black to move.
        self.fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"

    def toggle_orientation(self):
        """Server -> client sync: flip board orientation."""
        self.board_orientation = (
            "black" if self.board_orientation == "white" else "white"
        )


def index():
    return rx.vstack(
        rx.hstack(
            rx.button("Reset (server)", on_click=DemoState.reset_board),
            rx.button("Set preset: 1.e4 (server)", on_click=DemoState.set_preset_e2e4),
            rx.button("Flip board (server)", on_click=DemoState.toggle_orientation),
            spacing="2",
        ),
        rx.box(
            chessboard(
                fen=DemoState.fen,
                options={
                    "allowDragging": True,
                    "boardOrientation": DemoState.board_orientation,
                    # keep the PoC size sane; users can override freely
                    # (react-chessboard uses CSS sizing; width is controlled by the wrapper box)
                    # стрелки/подсветки позже можно добавить сюда же (arrows/squareStyles)
                },
                on_move=DemoState.on_move,
            ),
            width="420px",
        ),
        rx.text(DemoState.last_move),
        rx.code(DemoState.fen, white_space="pre-wrap"),
        rx.heading("Last payload (server received)"),
        rx.code(DemoState.last_payload_json, white_space="pre-wrap"),
        rx.heading("Moves"),
        rx.foreach(DemoState.moves, lambda m: rx.text(m)),
        spacing="3",
    )


app = rx.App()
app.add_page(index, route="/")
