from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import reflex as rx
from pydantic import BaseModel

UnknownNagMode = Literal["hide", "dollar"]


@dataclass(frozen=True, slots=True)
class NotationOptions:
    style: str = "chessbase"
    show_move_numbers: bool = True
    show_comments: bool = True
    show_nags: bool = True
    max_variation_depth: int | None = None
    unknown_nag_mode: UnknownNagMode = "hide"


_NAG_GLYPH: dict[int, str] = {
    1: "!",
    2: "?",
    3: "!!",
    4: "??",
    5: "!?",
    6: "?!",
}


def _opts(options: dict[str, Any] | None) -> NotationOptions:
    if not options:
        return NotationOptions()
    return NotationOptions(
        style=str(options.get("style", "chessbase")),
        show_move_numbers=bool(options.get("show_move_numbers", True)),
        show_comments=bool(options.get("show_comments", True)),
        show_nags=bool(options.get("show_nags", True)),
        max_variation_depth=(
            None
            if options.get("max_variation_depth") in (None, "")
            else int(options["max_variation_depth"])
        ),
        unknown_nag_mode=str(options.get("unknown_nag_mode", "hide")),  # type: ignore[arg-type]
    )


def _move_no(ply: int) -> int:
    return (ply + 1) // 2


def _move_number_prefix(ply: int, *, line_start: bool) -> str | None:
    """Return 'N.' / 'N...' prefix or None."""
    num = _move_no(ply)
    if ply % 2 == 1:
        return f"{num}."
    if line_start:
        return f"{num}..."
    return None


class NotationToken(BaseModel):
    kind: str
    text: str = ""
    node_id: str = ""
    san: str = ""


class NotationLine(BaseModel):
    indent: str  # e.g. "18px"
    tokens: list[NotationToken]


def _tok(kind: str, **kwargs: Any) -> NotationToken:
    return NotationToken(kind=kind, **kwargs)


def _render_comments_tokens(
    move: dict[str, Any],
    *,
    where: Literal["pre", "post"],
    o: NotationOptions,
) -> list[NotationToken]:
    if not o.show_comments:
        return []
    key = "preComments" if where == "pre" else "postComments"
    comments = move.get(key) or []
    out: list[NotationToken] = []
    if isinstance(comments, list):
        for c in comments:
            s = str(c).strip()
            if not s:
                continue
            out.append(_tok("comment", text=s))
            out.append(_tok("text", text=" "))

    if where == "post":
        ann = move.get("annotations") or {}
        text = ann.get("text")
        if isinstance(text, str) and text.strip():
            out.append(_tok("comment", text=text.strip()))
            out.append(_tok("text", text=" "))

    return out


def _render_nags_token(
    move: dict[str, Any], o: NotationOptions
) -> NotationToken | None:
    if not o.show_nags:
        return None
    nags = move.get("nags") or []
    if not isinstance(nags, list) or not nags:
        return None
    parts: list[str] = []
    for n in nags:
        try:
            ni = int(n)
        except Exception:
            continue
        g = _NAG_GLYPH.get(ni)
        if g:
            parts.append(g)
        elif o.unknown_nag_mode == "dollar":
            parts.append(f"${ni}")
    if not parts:
        return None
    return _tok("nag", text="".join(parts))


def _node(tree: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    nodes = tree.get("nodes") or {}
    if not isinstance(nodes, dict):
        return None
    n = nodes.get(node_id)
    return n if isinstance(n, dict) else None


def _move(tree: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    mbn = tree.get("moveByNode") or {}
    if not isinstance(mbn, dict):
        return None
    m = mbn.get(node_id)
    return m if isinstance(m, dict) else None


def _children(tree: dict[str, Any], node_id: str) -> list[str]:
    n = _node(tree, node_id) or {}
    ch = n.get("children") or []
    if not isinstance(ch, list):
        return []
    out: list[str] = []
    for x in ch:
        if isinstance(x, str) and x:
            out.append(x)
    return out


def _move_tokens(
    *,
    tree: dict[str, Any],
    node_id: str,
    line_start: bool,
    o: NotationOptions,
) -> list[NotationToken]:
    n = _node(tree, node_id)
    m = _move(tree, node_id)
    if not n or not m:
        return [_tok("text", text="?"), _tok("text", text=" ")]

    ply = int(n.get("ply") or 0)
    san = str(m.get("san") or "?")

    out: list[NotationToken] = []
    prefix = (
        _move_number_prefix(ply, line_start=line_start) if o.show_move_numbers else None
    )
    if prefix:
        out.append(_tok("moveno", text=prefix))
        out.append(_tok("text", text=" "))

    out.extend(_render_comments_tokens(m, where="pre", o=o))
    out.append(_tok("move", node_id=node_id, san=san))
    out.append(_tok("text", text=" "))

    nag = _render_nags_token(m, o)
    if nag is not None:
        out.append(nag)
        out.append(_tok("text", text=" "))

    out.extend(_render_comments_tokens(m, where="post", o=o))
    return out


def _build_mainline_lines(
    *,
    tree: dict[str, Any],
    start_node_id: str,
    depth: int,
    o: NotationOptions,
) -> list[NotationLine]:
    lines: list[NotationLine] = []
    cur = start_node_id
    tokens: list[NotationToken] = []
    first = True

    while True:
        ch = _children(tree, cur)
        if not ch:
            break
        main = ch[0]

        tokens.extend(
            _move_tokens(
                tree=tree,
                node_id=main,
                line_start=first,
                o=o,
            )
        )

        # Variations of the *node we just entered* (rule: after SAN leading into node).
        tokens.append(_tok("text", text=" "))
        lines.extend(_build_variation_lines(tree=tree, node_id=main, depth=depth, o=o))

        first = False
        cur = main

    if tokens:
        # Trim trailing spaces
        while tokens and tokens[-1].kind == "text" and tokens[-1].text == " ":
            tokens.pop()
        lines.insert(0, NotationLine(indent=f"{depth * 18}px", tokens=tokens))
    return lines


def _build_variation_lines(
    *,
    tree: dict[str, Any],
    node_id: str,
    depth: int,
    o: NotationOptions,
) -> list[NotationLine]:
    ch = _children(tree, node_id)
    if len(ch) <= 1:
        return []

    next_depth = depth + 1
    if o.max_variation_depth is not None and next_depth > o.max_variation_depth:
        return [
            NotationLine(
                indent=f"{next_depth * 18}px",
                tokens=[_tok("comment", text="(…)")],
            )
        ]

    lines: list[NotationLine] = []
    for v in ch[1:]:
        head: list[NotationToken] = [_tok("text", text="("), _tok("text", text=" ")]
        head.extend(_move_tokens(tree=tree, node_id=v, line_start=True, o=o))

        nested_lines: list[NotationLine] = []
        cur = v
        while True:
            ch2 = _children(tree, cur)
            if not ch2:
                break
            main = ch2[0]
            head.extend(_move_tokens(tree=tree, node_id=main, line_start=False, o=o))
            nested_lines.extend(
                _build_variation_lines(tree=tree, node_id=main, depth=next_depth, o=o)
            )
            cur = main

        # Trim trailing spaces then close ")"
        while head and head[-1].kind == "text" and head[-1].text == " ":
            head.pop()
        head.extend([_tok("text", text=" "), _tok("text", text=")")])

        lines.append(NotationLine(indent=f"{next_depth * 18}px", tokens=head))
        lines.extend(nested_lines)

    return lines


def build_notation_lines(
    tree: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> list[NotationLine]:
    """Server-side builder: PackedGameTree -> renderable lines.

    This returns a JSON-serializable structure that can be stored in Reflex State
    and rendered via `rx.foreach` without Python loops over Vars.
    """
    o = _opts(options)
    root_id = str(tree.get("rootId") or "n:root")
    return _build_mainline_lines(tree=tree, start_node_id=root_id, depth=0, o=o)


def _render_token(
    token: NotationToken, *, selected_id: rx.Var, on_select: rx.EventHandler
) -> rx.Component:
    kind = token.kind

    moveno_style = {"opacity": "0.75", "marginRight": "6px"}
    comment_style = {"opacity": "0.72", "fontStyle": "italic", "marginRight": "6px"}
    nag_style = {"opacity": "0.9", "marginRight": "6px"}

    move_style = {
        "display": "inline-block",
        "cursor": "pointer",
        "padding": "1px 3px",
        "borderRadius": "4px",
        "userSelect": "none",
        "marginRight": "6px",
    }
    move_style_sel = {
        **move_style,
        "backgroundColor": "rgba(59, 130, 246, 0.18)",
        "outline": "1px solid rgba(59, 130, 246, 0.35)",
    }

    return rx.cond(
        kind == "move",
        rx.cond(
            token.node_id == selected_id,
            rx.el.span(
                token.san,
                title=token.node_id,
                style=move_style_sel,
                on_click=on_select({"node_id": token.node_id}),
            ),
            rx.el.span(
                token.san,
                title=token.node_id,
                style=move_style,
                on_click=on_select({"node_id": token.node_id}),
            ),
        ),
        rx.cond(
            kind == "moveno",
            rx.el.span(token.text, style=moveno_style),
            rx.cond(
                kind == "comment",
                rx.el.span(token.text, style=comment_style),
                rx.cond(
                    kind == "nag",
                    rx.el.span(token.text, style=nag_style),
                    rx.el.span(token.text),
                ),
            ),
        ),
    )


def chess_notation(
    lines: list[NotationLine],
    selected_id: str,
    on_select: rx.EventHandler,
) -> rx.Component:
    """Render prebuilt notation lines (Var-friendly)."""
    wrapper_style = {
        "fontFamily": 'ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Noto Sans", "Liberation Sans", sans-serif',
        "fontSize": "14px",
        "lineHeight": "1.55",
        "color": "rgba(0,0,0,0.92)",
    }
    selected_var = rx.Var.create(selected_id)

    def render_line(line: NotationLine) -> rx.Component:
        return rx.el.div(
            rx.foreach(
                line.tokens,
                lambda t: _render_token(
                    t, selected_id=selected_var, on_select=on_select
                ),
            ),
            style={
                "marginLeft": line.indent,
                "whiteSpace": "pre-wrap",
                "wordBreak": "break-word",
            },
        )

    return rx.el.div(rx.foreach(lines, render_line), style=wrapper_style)
