import reflex as rx
from reflex_chess_viewer import chess_viewer


def index():
    return rx.center(
        rx.box(chess_viewer(), width="min(1200px, 100%)"),
        padding="16px",
        width="100%",
    )


app = rx.App()
app.add_page(index, route="/")
