Ниже — готовый набор спецификаций, оформленных так, чтобы вы могли **просто скопировать содержимое в файлы** в репозитории. Я даю:

1. **единое большое ТЗ** `SPEC.md` (Master Spec);
2. детальные уточняющие спецификации:

   * `packages/reflex-chessboard/SPEC.md`
   * `packages/reflex-chess-notation/SPEC.md`
   * `packages/reflex-chess-viewer/SPEC.md`
   * `apps/demo_pgn_viewer/SPEC.md`
   * (опционально, каркас) `packages/reflex-chess-trainer/SPEC.md`

Все документы согласованы между собой: единые термины, единые контракты (`PackedGameTree`, `node_id`), единые DoD.

---

## FILE: `SPEC.md` (Master Spec — единое большое ТЗ)

```markdown
# Chess Reflex Monorepo — Master Specification (SPEC)

## 1. Purpose

Build a monorepo containing multiple independently versioned and published PyPI packages for chess UI/components in Reflex:

- `reflex-chessboard` — chessboard component (UI, input, annotations).
- `reflex-chess-notation` — PGN notation component (UI, tree rendering, click-to-select moves).
- `reflex-chess-viewer` — reference integration (board + notation + navigation + PGN loading).
- `reflex-chess-trainer` — training modes framework (MVP: skeleton only; must not block the first release).

Additionally, provide one demo Reflex app that uses **all three** primary packages:
- A "PGN Viewer" app that loads PGN and allows browsing through the game tree.

## 2. Core Design Principles

1) **Strict separation of concerns**
- `reflex-chessboard` must not depend on notation/game-tree concepts.
- `reflex-chess-notation` must not depend on chessboard or manage FEN directly.
- `reflex-chess-viewer` (and later trainer) orchestrates synchronization.

2) **Single source of truth for the game state in viewer**
- Viewer owns `PackedGameTree` + `selected_id` (node_id).
- Chessboard receives only `fen` and annotation options.
- Notation receives only `PackedGameTree` and `selected_id`.

3) **Indices-first data model**
- The parsed PGN must be converted to a packed tree structure with lookup indices
  to support O(1)/fast operations:
  - next/prev mainline navigation
  - retrieving variants from a current node
  - reverse lookup by FEN (non-unique; list of nodes)

4) **Deterministic Node IDs**
- Each node is identified by a deterministic `node_id` derived from its `path` in the tree.
- This ID is stable across UI re-renders and serialization.

5) **Extensibility without breaking changes**
- MVP focuses on browsing and selection.
- Future work (editing, training modes, deeper PGN features) must extend the model
  rather than replacing it.

## 3. Monorepo Structure

```

repo/
SPEC.md
README.md
pyproject.toml
uv.lock
.github/workflows/
ci.yml
release.yml

packages/
reflex-chessboard/
SPEC.md
pyproject.toml
README.md
reflex_chessboard/...
frontend/...

```
reflex-chess-notation/
  SPEC.md
  pyproject.toml
  README.md
  reflex_chess_notation/...
  frontend/...

reflex-chess-viewer/
  SPEC.md
  pyproject.toml
  README.md
  reflex_chess_viewer/...

reflex-chess-trainer/
  SPEC.md
  pyproject.toml
  README.md
  reflex_chess_trainer/...
```

apps/
demo_pgn_viewer/
SPEC.md
pyproject.toml
rxconfig.py
demo_pgn_viewer/...

```

Each package is independently publishable to PyPI (separate `pyproject.toml` and version).
Demo app uses workspace/path dependencies to reference local packages.

## 4. Canonical Game Structure: PackedGameTree v1

### 4.1 Concept

A PGN game is represented as a tree:
- **Node** represents a *position* (FEN).
- **Edge** represents the *move* that leads from parent node to child node.
- The child node "owns" the move metadata that led into it (`moveByNode[child_id]`).

This makes "previous position + move that led here" trivial:
- prev node = `nodes[current].parent`
- move that led to current = `moveByNode[current]`

### 4.2 Types (JSON-compatible)

**Shape**
- Arrow: `{ "kind": "arrow", "color": "green|red|yellow|blue", "from": "e2", "to": "e4" }`
- Square highlight: `{ "kind": "square", "color": "green|red|yellow|blue", "square": "e4" }`

**MoveInfo**
- `san: string`
- `uci?: string` (optional)
- `nags: number[]`
- `preComments: string[]` (starting comments before SAN)
- `postComments: string[]` (comments after SAN)
- `annotations: {`
  - `eval?: { type: "pawns", value: number, depth?: number } | { type: "mate", value: number, depth?: number }`
  - `clock?: number` (seconds)
  - `emt?: number` (seconds)
  - `shapes: Shape[]`
  - `text?: string` (sanitized plain text)
  `}`

**Node**
- `id: string` (deterministic node_id)
- `ply: number` (0 for root)
- `fen: string` (FEN at this node; root = initialFen)
- `parent: string | null`
- `children: string[]` (child node_ids; `children[0]` = mainline continuation)

**PackedGameTree**
- `version: 1`
- `headers: Record<string, string>`
- `initialFen: string`
- `rootId: string`
- `nodes: Record<string, Node>`
- `moveByNode: Record<string, MoveInfo>` (root omitted)
- `nodeByFen: Record<string, string[]>` (FEN → list of node_ids; handle transpositions)
- `mainline: string[]` (node_ids from root following children[0])
- `nextMainline: Record<string, string|null>`
- `prevMainline: Record<string, string|null>`

### 4.3 Deterministic Node IDs

`node_id` is derived from the `path` in the tree (indices in `children[]`):

- root: `n:root`
- mainline child of root: `n:0`
- next mainline: `n:0.0`
- first side-variation at that point: `n:0.1`
- etc.

Rule: `"n:" + path.join(".")`, with root being `"n:root"`.

### 4.4 Key invariants

- Root node has `ply=0`, `parent=null`, `fen=initialFen`.
- For any non-root node:
  - `nodes[id].parent` exists
  - `moveByNode[id]` exists and describes the move into this node
- `children[0]` is mainline continuation; the rest are variations.
- `nodeByFen[fen]` stores a list (FEN can repeat).
- `mainline` includes root first.

## 5. Packages Responsibilities

### 5.1 reflex-chessboard
- Controlled chessboard: `fen` is the only position state.
- Supports DnD + click-to-move with client-side legality check.
- Emits `on_move` with `{from,to,piece,promotion?,fen,san}`.
- Supports annotations (arrows/square highlights) via options.

Must not implement PGN/tree/history.

### 5.2 reflex-chess-notation
- Renders a PackedGameTree as "ChessBase-like" notation.
- Highlights current node by `selected_id`.
- Emits `on_select({node_id})` on click.

Must not directly compute or manage FEN.

### 5.3 reflex-chess-viewer
- Reference integration:
  - Parses PGN into PackedGameTree.
  - Maintains `selected_id`.
  - Computes board `fen` and annotation options from `selected_id`.
  - Provides navigation controls (start/back/forward/end along mainline).
  - Provides PGN input for demo (paste/sample; file upload optional).

### 5.4 reflex-chess-trainer
- MVP: skeleton only.
- Must be compatible with PackedGameTree and node-based navigation.

## 6. PGN Parsing Requirements (Viewer)

Viewer must convert PGN to PackedGameTree with:
- computed FEN per node
- extracted comment annotations (eval/clock/emt/shapes/text) in tolerant mode
- populated indices (nodeByFen, mainline, prev/next)

Chessops is the preferred PGN parsing foundation on the frontend or a controlled internal pipeline;
the viewer must encapsulate parsing behind a module boundary.

## 7. Demo App Requirements: apps/demo_pgn_viewer

- Single app for entire monorepo.
- Uses `reflex-chess-viewer` as the main widget and, transitively or directly, the other packages.
- Must support:
  - load sample PGN
  - paste PGN and load
  - browsing by clicking notation moves and by navigation controls
- Displays debug info (selected_id, current FEN) for validation.

## 8. Tooling, CI, Release

- Python: `uv`, `ruff` (format+lint), `pytest`, plus one type checker (pyright or mypy).
- CI: lint/typecheck/tests + build frontends where applicable.
- Releases: publish each package independently via tags:
  - `reflex-chessboard-vX.Y.Z`
  - `reflex-chess-notation-vX.Y.Z`
  - `reflex-chess-viewer-vX.Y.Z`
  - `reflex-chess-trainer-vX.Y.Z`

## 9. MVP Implementation Plan (Deliverables)

Phase 1 — Monorepo skeleton
- repository layout
- workspace configuration
- CI baseline
- packages importable

Phase 2 — chessboard package migration
- move existing code into `packages/reflex-chessboard`
- preserve public API

Phase 3 — notation MVP
- PackedGameTree rendering (mainline + variations in parentheses)
- click-to-select => node_id event

Phase 4 — viewer MVP
- PGN -> PackedGameTree builder
- navigation
- board/notation sync
- annotation projection (shapes -> board options)

Phase 5 — demo app
- PGN input + sample
- embedded viewer

Phase 6 — docs and release pipelines
- per-package README and SPEC
- publishing automation

Definition of Done:
- demo app runs and allows browsing PGN
- selection sync works in both directions (click notation => board)
- mainline navigation works
- shapes (if present) render on board
- CI green
```

---

## FILE: `packages/reflex-chessboard/SPEC.md`

```markdown
# reflex-chessboard — SPEC

## 1. Scope

Provide a reusable Reflex chessboard component based on `react-chessboard` + `chess.js`.

This package is strictly about:
- rendering a board from FEN
- accepting input moves (DnD/click-to-move)
- local legality validation (no server round-trip)
- annotations (arrows + square highlights)
- piece sets/assets helpers

It must not implement PGN parsing, history, or game-tree logic.

## 2. Public API

### 2.1 Component

`chessboard(fen: str, options: dict | None = None, on_move: callable, on_arrows_change?: callable, on_resize?: callable)`

#### Props
- `fen: str`
  - `"start"` or a valid FEN.
  - Controlled: board position must always reflect this value.
- `options: dict | None`
  - Pass-through options to `react-chessboard`.
  - Plus shim extensions defined below.

#### Events

`on_move(payload: dict)`
- Fired after a successful legal move (DnD or click-to-move).
- Payload (minimum):
  - `from: str` (e.g. "e2")
  - `to: str` (e.g. "e4")
  - `piece: str` (consistent piece identifier)
  - `promotion: str | None` (q/r/b/n) if applicable
  - `fen: str` (FEN after move)
  - `san: str` (SAN move notation)

Optional events:
- `on_arrows_change({ "arrows": [...] })` when user draws arrows (if enabled)
- `on_resize({ "size": int })` when responsive mode observes container size change

### 2.2 Options: shim extensions (public, stable)

- `enableClickToMove: bool` (default True)
- `enableBuiltInHighlights: bool` (default True)
- `boardTheme: "default" | "gray"`
- `boardSize: int | str`
- `responsive: bool` (default False) — if True, ignore boardSize and use container sizing via ResizeObserver
- `pieceSet: "merida" | "unicode" | "assets/<name>" | ...`
- `piecesBaseUrl: str` (default "/pieces")

### 2.3 Options: react-chessboard pass-through (examples)
- `boardOrientation`
- `showNotation`
- `squareStyles`
- `arrows`
- `allowDrawingArrows`
- `arrowOptions`

## 3. Annotation Projection Contract

The package does not define a canonical annotation format, but must accept:
- `options["arrows"]` in react-chessboard format
- `options["squareStyles"]` for highlight squares

The `viewer` package will project `PackedGameTree` shapes to these options.

## 4. Assets helpers

Must provide helpers:
- `list_builtin_piece_sets() -> list[str]`
- `register_builtin_piece_assets(sets: Iterable[str] | None = None) -> None`
- `builtin_pieces_base_url() -> str`
- `builtin_piece_options(set_name: str) -> dict`

## 5. Non-functional Requirements

- Preserve existing README Quick Start and API wording (if already published).
- No breaking changes in events/payloads without major version bump.
- Minimal dependencies; keep package import time low.

## 6. Acceptance Tests (smoke)

- Import package and render `chessboard(fen="start")` in demo.
- Make a legal move: verify `on_move` payload contains required keys.
- Provide arrows and squareStyles: verify board renders them.
- Responsive mode: verify on_resize triggers on container size changes (basic).
```

---

## FILE: `packages/reflex-chess-notation/SPEC.md`

```markdown
# reflex-chess-notation — SPEC

## 1. Scope

Provide a reusable Reflex component that renders chess notation in a "ChessBase-like" style,
based on a canonical `PackedGameTree` structure.

The component:
- renders mainline moves inline with move numbers
- renders variations in parentheses (nested)
- supports comments and NAGs display
- highlights the currently selected node
- emits node selection events when user clicks a move

The component must not:
- compute FEN or mutate board state directly
- parse PGN itself in MVP (optional internally, but viewer is canonical for parsing)
- depend on `reflex-chessboard`

## 2. Public API

### Component

`chess_notation(tree: dict, selected_id: str, on_select: callable, options: dict | None = None)`

#### Props
- `tree: dict`
  - Must be a valid `PackedGameTree v1` object (see Master SPEC).
- `selected_id: str`
  - node_id of current selection.
- `options: dict | None`
  - Rendering options (see below).

#### Event
`on_select(payload: dict)`
- payload minimum: `{ "node_id": str }`

## 3. Rendering Rules (MVP)

### 3.1 Mainline layout
- Render mainline as:
  - `1. e4 e5 2. Nf3 Nc6 ...`
- White move at ply=1 is preceded by "1.".
- Black move at ply=2 is rendered after white move without repeating number.

### 3.2 Variations
- For a node, variations are its children beyond index 0.
- Render each variation as parentheses inserted at the point it branches:
  - `... e5 ( ...c5 ... ) ...`
- Support nesting.

### 3.3 Selection highlight
- The move that leads into `selected_id` must be visually highlighted.
- Root selection highlights nothing in moves, but may highlight "Start" marker.

### 3.4 NAG display
- Map NAG numbers to common glyphs at least for:
  - $1 !, $2 ?, $3 !!, $4 ??, $5 !?, $6 ?!
- For unknown NAG, either show `$N` or ignore (controlled by option).

### 3.5 Comments
- Support rendering of:
  - `preComments` (before SAN)
  - `postComments` (after SAN)
- MVP: show raw text and/or `annotations.text` when present.
- Do not require structured eval/clock rendering; can be added later.

## 4. Interaction Rules

- Clicking a move emits `on_select({node_id})` for the target child node.
- Optionally support:
  - hover events (future; not MVP)
  - context actions (future; not MVP)

## 5. Options (MVP)

- `style: "chessbase"` (default)
- `show_move_numbers: bool` (default True)
- `show_comments: bool` (default True)
- `show_nags: bool` (default True)
- `max_variation_depth?: int` (optional; if set, collapse deeper nesting)
- `unknown_nag_mode: "hide"|"dollar"` (default "hide")

## 6. Acceptance Tests (smoke)

- Render a small PackedGameTree with one variation and comments:
  - verify layout includes parentheses
  - verify clicking a move fires node_id
  - verify selected_id highlights correct element
```

---

## FILE: `packages/reflex-chess-viewer/SPEC.md`

```markdown
# reflex-chess-viewer — SPEC

## 1. Scope

Provide a reference integration component that composes:
- `reflex-chessboard`
- `reflex-chess-notation`

It owns:
- PGN loading
- parsing/building PackedGameTree
- selection state (`selected_id`)
- navigation along mainline
- projection of current node into chessboard FEN + annotations

The viewer is the canonical place for game model + indices in MVP.

## 2. Public API

### Component

`chess_viewer(pgn: str | None = None, initial_node_id: str | None = None, board_options: dict | None = None, notation_options: dict | None = None, allow_board_input: bool = False, options: dict | None = None)`

#### Props
- `pgn: str | None`
  - If provided, auto-load on mount.
- `initial_node_id: str | None`
  - Defaults to root.
- `board_options: dict | None`
  - Passed to chessboard.
- `notation_options: dict | None`
  - Passed to notation.
- `allow_board_input: bool`
  - MVP default False (read-only viewer).
  - If True, viewer may accept new moves from board; behavior beyond MVP can be TODO.
- `options: dict | None`
  - viewer-level options: show toolbar, show PGN input panel, etc.

## 3. Internal Model

Viewer must build and hold:
- `tree: PackedGameTree`
- `selected_id: str`

Derived:
- `current_node = tree.nodes[selected_id]`
- `current_fen = current_node.fen`
- `current_shapes = tree.moveByNode[selected_id].annotations.shapes` (if selected is non-root)
  - if root selected => shapes empty

## 4. PackedGameTree Builder

### 4.1 Deterministic node_id assignment

During parsing/building, assign node_id based on traversal path:
- root = n:root
- for each child at index i:
  - child_path = parent_path + [i]
  - child_id = n:<path joined by dot>

### 4.2 Builder output requirements
Must populate:
- nodes
- moveByNode (except root)
- nodeByFen
- mainline + prevMainline + nextMainline

### 4.3 Tolerant comment parsing
- Extract shapes/eval/clock/emt when possible.
- If extraction fails for a comment chunk, keep it in text.
- Never fail entire PGN load because of a malformed comment; show best-effort.

### 4.4 Transpositions
- nodeByFen maps fen -> list of node_id
- viewer selection uses node_id; never rely on "fen is unique".

## 5. UI Behavior (MVP)

### 5.1 Layout
- Top toolbar: Start, Back, Forward, End (mainline navigation)
- Main content: board + notation
- Optional: PGN input panel (paste/sample)

### 5.2 Navigation actions
- Start: select rootId
- End: select last node of mainline
- Back: select prevMainline[selected_id] if exists
- Forward: select nextMainline[selected_id] if exists

### 5.3 Notation selection
- notation `on_select({node_id})` sets selected_id.
- board updates fen accordingly.

### 5.4 Board rendering
- board receives `fen=current_fen`
- board receives annotation options projected from `current_shapes`
  - shapes -> react-chessboard `arrows` and `squareStyles`

### 5.5 PGN loading
Viewer must support at least:
- set PGN from prop on init
- load sample PGN (hardcoded string)
- allow paste PGN via textarea in demo mode
File upload is optional.

## 6. Shape-to-Board Projection

Implement a helper:
`project_shapes_to_board_options(shapes: Shape[]) -> dict`
- returns:
  - `arrows: [{startSquare,endSquare,color}]`
  - `squareStyles: { "e4": { ...style... }, ... }`

Color mapping:
- green/red/yellow/blue mapped to chosen CSS colors (define constants).
- Keep mapping stable.

## 7. Acceptance Tests (smoke)

- Load sample PGN:
  - tree built
  - root selected => fen initial
- Click a move in notation:
  - selected_id updates
  - fen changes
- Navigation buttons:
  - prev/next follow mainline correctly
- If PGN contains shapes:
  - board receives arrows/squareStyles and renders them
```

---

## FILE: `apps/demo_pgn_viewer/SPEC.md`

```markdown
# demo_pgn_viewer — SPEC

## 1. Purpose

Provide a single demo application for the entire monorepo that demonstrates:
- `reflex-chessboard`
- `reflex-chess-notation`
- `reflex-chess-viewer`

Primary goal: validate integration via a PGN browsing workflow.

## 2. Functional Requirements (MVP)

- One page `/` that includes:
  - textarea for PGN input
  - "Load" button
  - "Load sample" button
  - viewer widget rendering board + notation

- Display debug info:
  - current selected node_id
  - current FEN
  - optionally current SAN / move number

## 3. Technical Requirements

- App must use local workspace dependencies (path references to packages).
- Run command:
  - `uv run reflex run`
- Keep code minimal and focused on integration.

## 4. UX Requirements

- Responsive enough to be usable on a typical desktop width.
- Clear separation: input panel and viewer area.

## 5. Acceptance

- Demo launches successfully.
- User can paste a PGN and browse via click + navigation.
- No direct imports from package internals; only public APIs.
```

---

## FILE: `packages/reflex-chess-trainer/SPEC.md` (опционально, каркас)

```markdown
# reflex-chess-trainer — SPEC (Skeleton)

## 1. Scope (MVP)

Provide an extensible framework for training modes built on:
- PackedGameTree v1
- node-based navigation and variant handling

MVP only requires:
- module/package skeleton
- interfaces/protocols for modes
- one minimal placeholder mode (no complex UX)

This package must not block the release of chessboard/notation/viewer.

## 2. Core Concepts

- Trainer consumes a `PackedGameTree` and a current `node_id`.
- A mode defines:
  - what constitutes a "correct" next move (often: children[0] or a subset)
  - progression rules
  - feedback rules

## 3. Proposed Interfaces

- `TrainerMode` (protocol):
  - `name: str`
  - `init(tree) -> state`
  - `prompt(state) -> dict` (what to show)
  - `submit_move(state, node_id_or_move) -> result`
  - `advance(state) -> state`

## 4. Deliverables (MVP)

- Create package layout and minimal docs.
- Provide a placeholder `GuessMainlineMove` mode stub that:
  - shows current position
  - expects user to choose mainline next move (implementation can be TODO)

## 5. Non-functional
- Keep dependencies minimal.
- All future work must remain compatible with PackedGameTree.
```

---
