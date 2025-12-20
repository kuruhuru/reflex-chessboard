import reflex as rx

config = rx.Config(
    app_name="chessboard_demo",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)