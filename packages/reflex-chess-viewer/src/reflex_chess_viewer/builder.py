from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

import chess.pgn

from reflex_chess_model.types import MoveInfo, PackedGameTree


def _node_id_from_path(path: list[int]) -> str:
    if not path:
        return "n:root"
    return "n:" + ".".join(str(i) for i in path)


def _split_comment(text: str | None) -> list[str]:
    if not text:
        return []
    s = str(text).strip()
    if not s:
        return []
    return [s]


@dataclass(frozen=True, slots=True)
class GameTreeBuilder:
    def build(self, pgn: str) -> PackedGameTree:
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            raise ValueError("PGN: no game found")

        headers = {str(k): str(v) for k, v in dict(game.headers).items()}
        board0 = game.board()
        initial_fen = headers.get("FEN") or board0.fen()

        root_id = "n:root"
        nodes: dict[str, dict[str, Any]] = {
            root_id: {
                "id": root_id,
                "ply": 0,
                "fen": initial_fen,
                "parent": None,
                "children": [],
            }
        }
        move_by_node: dict[str, MoveInfo] = {}
        node_by_fen: dict[str, list[str]] = {initial_fen: [root_id]}

        def walk(parent: chess.pgn.GameNode, parent_id: str, parent_path: list[int]) -> None:
            variations = list(parent.variations)
            children_ids: list[str] = []

            for i, child in enumerate(variations):
                path = [*parent_path, i]
                node_id = _node_id_from_path(path)

                # Board after move.
                b = child.board()
                fen = b.fen()

                nodes[node_id] = {
                    "id": node_id,
                    "ply": child.ply(),
                    "fen": fen,
                    "parent": parent_id,
                    "children": [],
                }
                node_by_fen.setdefault(fen, []).append(node_id)

                # MoveInfo for the node (move that leads into it).
                try:
                    san = parent.board().san(child.move)
                except Exception:
                    san = "?"
                uci = None
                try:
                    uci = child.move.uci()
                except Exception:
                    uci = None

                nags = sorted(int(n) for n in getattr(child, "nags", set()) or set())
                pre = _split_comment(getattr(child, "starting_comment", None))
                post = _split_comment(getattr(child, "comment", None))

                mi: dict[str, Any] = {
                    "san": san,
                    "nags": nags,
                    "preComments": pre,
                    "postComments": post,
                    "annotations": {"shapes": []},
                }
                if uci:
                    mi["uci"] = uci
                move_by_node[node_id] = mi  # type: ignore[assignment]

                children_ids.append(node_id)
                walk(child, node_id, path)

            nodes[parent_id]["children"] = children_ids

        walk(game, root_id, [])

        # mainline indices
        mainline: list[str] = [root_id]
        cur = root_id
        while True:
            ch = nodes[cur]["children"]
            if not ch:
                break
            cur = ch[0]
            mainline.append(cur)

        next_mainline: dict[str, str | None] = {}
        prev_mainline: dict[str, str | None] = {}
        for idx, nid in enumerate(mainline):
            prev_mainline[nid] = mainline[idx - 1] if idx > 0 else None
            next_mainline[nid] = mainline[idx + 1] if idx + 1 < len(mainline) else None

        return {
            "version": 1,
            "headers": headers,
            "initialFen": initial_fen,
            "rootId": root_id,
            "nodes": nodes,  # type: ignore[return-value]
            "moveByNode": {k: v for k, v in move_by_node.items() if k != root_id},
            "nodeByFen": node_by_fen,
            "mainline": mainline,
            "nextMainline": next_mainline,
            "prevMainline": prev_mainline,
        }


