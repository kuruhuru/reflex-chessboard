export type ColorName = "green" | "red" | "yellow" | "blue";

export type ArrowShape = {
  kind: "arrow";
  color: ColorName;
  from: string;
  to: string;
};

export type SquareShape = {
  kind: "square";
  color: ColorName;
  square: string;
};

export type Shape = ArrowShape | SquareShape;

export type EvalPawns = { type: "pawns"; value: number; depth?: number };
export type EvalMate = { type: "mate"; value: number; depth?: number };
export type Eval = EvalPawns | EvalMate;

export type MoveAnnotations = {
  eval?: Eval;
  clock?: number;
  emt?: number;
  shapes?: Shape[];
  text?: string;
};

export type MoveInfo = {
  san: string;
  uci?: string;
  nags: number[];
  preComments: string[];
  postComments: string[];
  annotations: MoveAnnotations;
};

export type Node = {
  id: string;
  ply: number;
  fen: string;
  parent: string | null;
  children: string[];
};

export type PackedGameTreeV1 = {
  version: 1;
  headers: Record<string, string>;
  initialFen: string;
  rootId: string;
  nodes: Record<string, Node>;
  moveByNode: Record<string, MoveInfo>;
  nodeByFen: Record<string, string[]>;
  mainline: string[];
  nextMainline: Record<string, string | null>;
  prevMainline: Record<string, string | null>;
};


