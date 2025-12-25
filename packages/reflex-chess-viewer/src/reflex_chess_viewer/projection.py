from __future__ import annotations

from typing import Any

from reflex_chess_model.types import Shape


_COLOR = {
    "green": "rgba(34, 197, 94, 0.85)",
    "red": "rgba(239, 68, 68, 0.85)",
    "yellow": "rgba(234, 179, 8, 0.85)",
    "blue": "rgba(59, 130, 246, 0.85)",
}


def project_shapes_to_board_options(shapes: list[Shape]) -> dict[str, Any]:
    """Project PackedGameTree shapes into react-chessboard options."""
    arrows: list[dict[str, Any]] = []
    square_styles: dict[str, dict[str, Any]] = {}

    for s in shapes or []:
        kind = s.get("kind")
        color = _COLOR.get(s.get("color"), "rgba(0,0,0,0.6)")
        if kind == "arrow":
            arrows.append(
                {
                    "startSquare": s.get("from"),
                    "endSquare": s.get("to"),
                    "color": color,
                }
            )
        elif kind == "square":
            sq = s.get("square")
            if sq:
                # last one wins (deterministic)
                square_styles[str(sq)] = {"backgroundColor": color.replace("0.85", "0.28")}

    return {"arrows": arrows, "squareStyles": square_styles}


