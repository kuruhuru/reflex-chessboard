from __future__ import annotations

from typing import Literal, TypedDict

from typing_extensions import NotRequired


ColorName = Literal["green", "red", "yellow", "blue"]


ArrowShape = TypedDict(
    "ArrowShape",
    {
        "kind": Literal["arrow"],
        "color": ColorName,
        "from": str,
        "to": str,
    },
)


class SquareShape(TypedDict):
    kind: Literal["square"]
    color: ColorName
    square: str


Shape = ArrowShape | SquareShape


class EvalPawns(TypedDict):
    type: Literal["pawns"]
    value: float
    depth: NotRequired[int]


class EvalMate(TypedDict):
    type: Literal["mate"]
    value: int
    depth: NotRequired[int]


Eval = EvalPawns | EvalMate


class MoveAnnotations(TypedDict, total=False):
    eval: Eval
    clock: float  # seconds
    emt: float  # seconds
    shapes: list[Shape]
    text: str


class MoveInfo(TypedDict):
    san: str
    uci: NotRequired[str]
    nags: list[int]
    preComments: list[str]
    postComments: list[str]
    annotations: MoveAnnotations


class Node(TypedDict):
    id: str
    ply: int
    fen: str
    parent: str | None
    children: list[str]


class PackedGameTree(TypedDict):
    version: Literal[1]
    headers: dict[str, str]
    initialFen: str
    rootId: str
    nodes: dict[str, Node]
    moveByNode: dict[str, MoveInfo]  # root omitted
    nodeByFen: dict[str, list[str]]
    mainline: list[str]
    nextMainline: dict[str, str | None]
    prevMainline: dict[str, str | None]


