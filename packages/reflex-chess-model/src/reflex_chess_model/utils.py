from __future__ import annotations

from typing import Any

from .types import Node, PackedGameTree


def is_root(node_id: str) -> bool:
    return node_id == "n:root"


def get_node(tree: PackedGameTree, node_id: str) -> Node:
    try:
        return tree["nodes"][node_id]
    except KeyError as e:
        raise KeyError(f"Unknown node_id: {node_id}") from e


def get_header(tree: PackedGameTree, key: str, default: str | None = None) -> str | None:
    headers: dict[str, Any] = tree.get("headers", {})  # type: ignore[assignment]
    value = headers.get(key, default)
    return None if value is None else str(value)


