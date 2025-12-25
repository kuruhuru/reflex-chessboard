from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .utils import is_root


def _err(prefix: str, msg: str) -> ValueError:
    return ValueError(f"{prefix}: {msg}")


def validate_tree(tree: Mapping[str, Any]) -> None:
    """Soft validation for PackedGameTree v1.

    Raises ValueError with a human-readable message on schema/invariant violations.
    """
    if not isinstance(tree, Mapping):
        raise _err("PackedGameTree", "expected a mapping/dict")

    version = tree.get("version")
    if version != 1:
        raise _err("PackedGameTree.version", f"expected 1, got {version!r}")

    for k in ("headers", "initialFen", "rootId", "nodes", "moveByNode", "nodeByFen", "mainline", "nextMainline", "prevMainline"):
        if k not in tree:
            raise _err("PackedGameTree", f"missing required key {k!r}")

    root_id = tree["rootId"]
    if not isinstance(root_id, str) or not root_id:
        raise _err("PackedGameTree.rootId", "expected non-empty str")

    nodes = tree["nodes"]
    if not isinstance(nodes, Mapping):
        raise _err("PackedGameTree.nodes", "expected mapping node_id -> Node")

    if root_id not in nodes:
        raise _err("PackedGameTree.nodes", f"rootId {root_id!r} is not present in nodes")

    move_by_node = tree["moveByNode"]
    if not isinstance(move_by_node, Mapping):
        raise _err("PackedGameTree.moveByNode", "expected mapping node_id -> MoveInfo")
    if root_id in move_by_node:
        raise _err("PackedGameTree.moveByNode", "root must be omitted")

    mainline = tree["mainline"]
    if not isinstance(mainline, list) or not mainline:
        raise _err("PackedGameTree.mainline", "expected non-empty list of node_ids")
    if mainline[0] != root_id:
        raise _err("PackedGameTree.mainline", "expected mainline[0] == rootId")

    def check_node(node_id: str, node: Any) -> None:
        if not isinstance(node, Mapping):
            raise _err(f"Node[{node_id}]", "expected mapping")
        if node.get("id") != node_id:
            raise _err(f"Node[{node_id}].id", f"expected {node_id!r}")
        ply = node.get("ply")
        if not isinstance(ply, int) or ply < 0:
            raise _err(f"Node[{node_id}].ply", "expected int >= 0")
        fen = node.get("fen")
        if not isinstance(fen, str) or not fen:
            raise _err(f"Node[{node_id}].fen", "expected non-empty str")
        parent = node.get("parent")
        if parent is not None and not isinstance(parent, str):
            raise _err(f"Node[{node_id}].parent", "expected str|null")
        children = node.get("children")
        if not isinstance(children, list):
            raise _err(f"Node[{node_id}].children", "expected list[str]")
        for c in children:
            if not isinstance(c, str) or not c:
                raise _err(f"Node[{node_id}].children", "expected list of non-empty str node_ids")
            if c not in nodes:
                raise _err(f"Node[{node_id}].children", f"child {c!r} missing from nodes")

        if node_id == root_id or is_root(node_id):
            if parent is not None:
                raise _err(f"Node[{node_id}].parent", "root parent must be null")
            if ply != 0:
                raise _err(f"Node[{node_id}].ply", "root ply must be 0")
        else:
            if parent is None:
                raise _err(f"Node[{node_id}].parent", "non-root parent must be set")
            if parent not in nodes:
                raise _err(f"Node[{node_id}].parent", f"parent {parent!r} missing from nodes")
            if node_id not in move_by_node:
                raise _err(f"PackedGameTree.moveByNode[{node_id}]", "missing MoveInfo for non-root node")

    for nid, n in nodes.items():
        if not isinstance(nid, str) or not nid:
            raise _err("PackedGameTree.nodes", "node_id keys must be non-empty strings")
        check_node(nid, n)

    node_by_fen = tree["nodeByFen"]
    if not isinstance(node_by_fen, Mapping):
        raise _err("PackedGameTree.nodeByFen", "expected mapping fen -> list[node_id]")
    for fen, ids in node_by_fen.items():
        if not isinstance(fen, str) or not fen:
            raise _err("PackedGameTree.nodeByFen", "fen keys must be non-empty strings")
        if not isinstance(ids, list):
            raise _err(f"PackedGameTree.nodeByFen[{fen!r}]", "expected list[node_id]")
        for nid in ids:
            if nid not in nodes:
                raise _err(f"PackedGameTree.nodeByFen[{fen!r}]", f"node_id {nid!r} missing from nodes")


