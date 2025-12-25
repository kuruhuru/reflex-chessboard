from __future__ import annotations

from typing import Annotated, Any

import reflex as rx
from reflex.utils.imports import ImportVar


class Chessboard(rx.Component):
    # NOTE: We intentionally do NOT import a local `.jsx` file from `/public` or `/assets`.
    # Vite forbids module imports from `/public` (see error: "Cannot import non-asset file ... inside /public").
    # Instead, we inject the shim's JS into the page module and load npm deps only on the client via ClientSide().
    tag = "ReflexChessboardShim"

    lib_dependencies = ["react-chessboard@5.8.6", "chess.js@1.4.0"]

    # Props (Python -> React).
    fen: str = "start"
    options: dict[str, Any] | None = None

    # Events (React -> Python). Reflex will expose this to JS as `onMove`.
    # Provide an ArgsSpec so handlers can accept a payload dict, e.g. `def on_move(self, payload: dict): ...`
    on_move: Annotated[rx.EventHandler, lambda payload: [payload]]

    # Optional: user-drawn arrows from the board (when allowDrawingArrows is enabled).
    # NOTE: keep type origin EventHandler so Reflex treats it as an event trigger.
    on_arrows_change: Annotated[rx.EventHandler, lambda payload: [payload]] = None  # type: ignore[assignment]

    # Optional: notify server about responsive board size changes (container resize).
    on_resize: Annotated[rx.EventHandler, lambda payload: [payload]] = None  # type: ignore[assignment]

    def add_imports(self):
        # Imports required for injected shim code.
        return {
            "react": [
                ImportVar(tag="useCallback"),
                ImportVar(tag="useEffect"),
                ImportVar(tag="useId"),
                ImportVar(tag="useMemo"),
                ImportVar(tag="useRef"),
                ImportVar(tag="useState"),
            ],
            "$/utils/context": [ImportVar(tag="ClientSide")],
            "@emotion/react": [ImportVar(tag="jsx")],
        }

    def _get_custom_code(self) -> str:
        # Inject a client-only loader that dynamically imports heavy deps (react-chessboard + chess.js)
        # and returns the actual shim component. This avoids SSR issues and avoids importing from /public.
        #
        # IMPORTANT: the symbol name MUST match `tag` so the compiled page can render it.
        return r"""
const ReflexChessboardShim = ClientSide(async () => {
  const [reactChessboardMod, chessJsMod] = await Promise.all([
    import("react-chessboard"),
    import("chess.js"),
  ]);

  // Handle both ESM/CJS export shapes.
  const ChessboardComp = reactChessboardMod?.Chessboard ?? reactChessboardMod?.default ?? reactChessboardMod;
  const defaultPieces = reactChessboardMod?.defaultPieces;
  const ChessCtor =
    chessJsMod?.Chess ??
    chessJsMod?.default?.Chess ??
    chessJsMod?.default ??
    chessJsMod;

  return function ReflexChessboardShimInner(props) {
    const { fen, options, onMove, onArrowsChange, onResize } = props;

    const reactId = useId();
    const debug = (options && options.debug) ? true : false;
    const chessRef = useRef(null);
    const startFenRef = useRef(null);
    const [localFen, setLocalFen] = useState(fen || "start");
    const [selectedSquare, setSelectedSquare] = useState(null);
    const [lastMove, setLastMove] = useState({ from: null, to: null });
    const containerRef = useRef(null);
    const [responsiveSize, setResponsiveSize] = useState(null);
    const lastSentSizeRef = useRef(null);
    const resizeDebounceRef = useRef(null);
    const lastSentArrowsRef = useRef(null);

    // Initialize chess.js once.
    if (!chessRef.current) {
      chessRef.current = new ChessCtor();
      try {
        startFenRef.current = chessRef.current.fen();
      } catch (_e) {
        startFenRef.current = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
      }
      if (fen && fen !== "start") {
        try {
          chessRef.current.load(fen);
        } catch {
          chessRef.current.reset();
        }
      }
    }

    // Sync server fen -> local state.
    useEffect(() => {
      if (!fen) return;
      // Normalize incoming "start" -> start FEN to keep react-chessboard happy.
      const normalized = (fen === "start") ? (startFenRef.current || "start") : fen;
      if (normalized === localFen) return;
      try {
        if (fen === "start") chessRef.current.reset();
        else chessRef.current.load(fen);
        setLocalFen(normalized);
        setSelectedSquare(null);
        setLastMove({ from: null, to: null });
      } catch {
        // ignore invalid fen
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [fen]);

    useEffect(() => {
      if (debug) {
        console.error("[reflex-chessboard] shim mounted", { fen, localFen });
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Optional: make the board responsive to its container size (useful for resizable demo containers).
    useEffect(() => {
      const enabled = !!(options && options.responsive);
      if (!enabled) return;

      const el = containerRef.current;
      if (!el) return;

      const update = () => {
        // Measure the host container (parent) to avoid feedback loops:
        // our inner div is sized to 100% and therefore reflects the parent's *content box*,
        // which can be smaller than the CSS width due to borders. If we send that back to
        // Python and set width to it, we shrink by the border size repeatedly.
        const host = el.parentElement || el;
        const rect = host.getBoundingClientRect?.();
        if (!rect) return;
        const w = Math.round(rect.width);
        const h = Math.round(rect.height);
        const sizeForBoard = Math.floor(Math.min(w, h));
        if (sizeForBoard > 0) {
          setResponsiveSize(sizeForBoard);

          // If the user provided an onResize handler, notify server (debounced) so
          // Python state can reflect the resized container.
          if (onResize) {
            if (resizeDebounceRef.current) clearTimeout(resizeDebounceRef.current);
            resizeDebounceRef.current = setTimeout(() => {
              // In our demo the user resizes horizontally, so use width as the canonical size.
              if (lastSentSizeRef.current !== w) {
                lastSentSizeRef.current = w;
                onResize({ size: w });
              }
            }, 120);
          }
        }
      };

      update();

      // Prefer ResizeObserver when available.
      if (typeof ResizeObserver !== "undefined") {
        const ro = new ResizeObserver(() => update());
        ro.observe(el);
        return () => {
          ro.disconnect();
          if (resizeDebounceRef.current) clearTimeout(resizeDebounceRef.current);
        };
      }

      window.addEventListener("resize", update);
      return () => {
        window.removeEventListener("resize", update);
        if (resizeDebounceRef.current) clearTimeout(resizeDebounceRef.current);
      };
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [options]);

    function inferPromotion(sourceSquare, targetSquare) {
      try {
        const moving = chessRef.current?.get?.(sourceSquare);
        const isPawn = moving?.type === "p";
        if (!isPawn) return undefined;
        const rank = targetSquare?.[1];
        if (rank === "8" || rank === "1") return "q";
      } catch (_e) {
        // ignore
      }
      return undefined;
    }

    function applyMove(from, to, pieceTypeForPayload) {
      const promotion = inferPromotion(from, to);
      let result = null;
      try {
        result = chessRef.current.move({
          from,
          to,
          promotion,
        });
      } catch (e) {
        console.error("[reflex-chessboard] chess.js move error", e, {
          from,
          to,
          promotion,
          fen: chessRef.current?.fen?.(),
        });
        return { ok: false };
      }

      if (!result) return { ok: false };

      const newFen = chessRef.current.fen();
      setLocalFen(newFen);
      setSelectedSquare(null);
      setLastMove({ from, to });

      if (onMove) {
        onMove({
          from,
          to,
          piece: pieceTypeForPayload ?? null,
          promotion: promotion ?? null,
          fen: newFen,
          san: result.san ?? null,
        });
      }

      return { ok: true };
    }

    // react-chessboard v5.x uses an Options API:
    // options.onPieceDrop({ piece, sourceSquare, targetSquare }) => boolean
    function onPieceDrop(args) {
      const sourceSquare = args?.sourceSquare;
      const targetSquare = args?.targetSquare;
      const piece = args?.piece;
      if (debug) {
        console.error("[reflex-chessboard] onPieceDrop", { sourceSquare, targetSquare, piece, localFen });
        try { document.title = `[drop] ${sourceSquare}->${targetSquare}`; } catch (_e) {}
      }
      if (!sourceSquare || !targetSquare) return false;

      const res = applyMove(sourceSquare, targetSquare, piece?.pieceType);
      if (!res.ok) {
        console.warn("[reflex-chessboard] illegal move rejected", {
          sourceSquare,
          targetSquare,
          piece,
          fen: chessRef.current?.fen?.(),
        });
      }
      return res.ok;
    }

    function normalizeClickedSquare(arg, arg2) {
      // react-chessboard typically calls:
      // - onSquareClick(square: string)
      // - onPieceClick(piece: string, square: string)
      // Some wrappers may pass objects; support both.
      if (typeof arg === "string") return arg;
      if (typeof arg2 === "string") return arg2;
      const maybe = arg?.square ?? arg?.targetSquare ?? arg?.sourceSquare;
      return (typeof maybe === "string") ? maybe : null;
    }

    function squareHasPiece(square) {
      try {
        return !!chessRef.current?.get?.(square);
      } catch (_e) {
        return false;
      }
    }

    function handleClickToMove(square, pieceFromEvent) {
      if (!square) return;

      if (!selectedSquare) {
        // Only select if user clicked a square with a piece.
        if (pieceFromEvent || squareHasPiece(square)) setSelectedSquare(square);
        return;
      }

      // NOTE: Do not toggle-off selection when clicking the same square.
      // Depending on the browser/DnD sensors, a single user click can trigger:
      //   onSquareMouseDown (select) -> onSquareClick (same square)
      // which would immediately clear selection and make click-to-move unusable.
      if (selectedSquare === square) return;

      const res = applyMove(selectedSquare, square, null);
      if (!res.ok) {
        if (pieceFromEvent || squareHasPiece(square)) setSelectedSquare(square);
      }
    }

    // Click-to-move (client-side) using chess.js for instant validation.
    // NOTE: In some DnD setups, `click` can be swallowed; we also wire `onSquareMouseDown`.
    const onSquareClick = useCallback((arg) => {
      const enableClickToMove = (options && options.enableClickToMove !== undefined)
        ? !!options.enableClickToMove
        : true;
      if (!enableClickToMove) return;

      const square = normalizeClickedSquare(arg, null);
      const pieceFromEvent = (typeof arg === "object" && arg) ? (arg.piece ?? null) : null;
      handleClickToMove(square, pieceFromEvent);
    }, [options, selectedSquare]);

    const onSquareMouseDown = useCallback((arg, e) => {
      const enableClickToMove = (options && options.enableClickToMove !== undefined)
        ? !!options.enableClickToMove
        : true;
      if (!enableClickToMove) return;
      // Only left button.
      if (e && e.button !== undefined && e.button !== 0) return;

      const square = normalizeClickedSquare(arg, null);
      const pieceFromEvent = (typeof arg === "object" && arg) ? (arg.piece ?? null) : null;
      handleClickToMove(square, pieceFromEvent);
    }, [options, selectedSquare]);

    const onPieceClick = useCallback((args) => {
      // react-chessboard calls onPieceClick({ isSparePiece, piece: { pieceType }, square })
      const enableClickToMove = (options && options.enableClickToMove !== undefined)
        ? !!options.enableClickToMove
        : true;
      if (!enableClickToMove) return;

      const sq = normalizeClickedSquare(args, null);
      if (!sq) return;
      handleClickToMove(sq, true);
    }, [options, selectedSquare]);

    const onArrowsChangeInternal = useCallback((args) => {
      if (!onArrowsChange) return;
      const arrows = args?.arrows ?? [];
      // Deduplicate to avoid spamming the server on remount/resize loops.
      const key = JSON.stringify(arrows);
      if (lastSentArrowsRef.current === key) return;
      lastSentArrowsRef.current = key;
      onArrowsChange({ arrows });
    }, [onArrowsChange]);

    function makeUnicodePieces() {
      const map = {
        wK: "♔", wQ: "♕", wR: "♖", wB: "♗", wN: "♘", wP: "♙",
        bK: "♚", bQ: "♛", bR: "♜", bB: "♝", bN: "♞", bP: "♟",
      };
      const mk = (key) => (props) => {
        const ch = map[key] || "?";
        // Text outline for readability on different square colors.
        const style = {
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          lineHeight: 1,
          fontSize: "34px",
          userSelect: "none",
          // mimic outline similar to SVG pieces
          textShadow: "0 0 2px rgba(0,0,0,0.85)",
          ...(props?.svgStyle || {}),
        };
        return jsx("div", { style, children: ch });
      };
      return {
        wK: mk("wK"), wQ: mk("wQ"), wR: mk("wR"), wB: mk("wB"), wN: mk("wN"), wP: mk("wP"),
        bK: mk("bK"), bQ: mk("bQ"), bR: mk("bR"), bB: mk("bB"), bN: mk("bN"), bP: mk("bP"),
      };
    }

    function makeSvgAssetPieces(baseUrl, setName) {
      const pieceKeys = ["wK","wQ","wR","wB","wN","wP","bK","bQ","bR","bB","bN","bP"];
      const normalizeBase = (baseUrl || "/pieces").replace(/\/+$/, "");
      const normalizeSet = String(setName || "").replace(/^\/+|\/+$/g, "");
      const mk = (key) => (props) => {
        const src = `${normalizeBase}/${normalizeSet}/${key}.svg`;
        const style = {
          width: "100%",
          height: "100%",
          display: "block",
          userSelect: "none",
          ...(props?.svgStyle || {}),
        };
        return jsx("img", { src, style, draggable: false, alt: key });
      };
      const out = {};
      for (const k of pieceKeys) out[k] = mk(k);
      return out;
    }

    const mergedOptions = useMemo(() => {
      const id = (options && options.id) ? options.id : `reflex-chessboard-${reactId}`;
      const boardTheme = options?.boardTheme ?? "default";
      const pieceSetRaw = options?.pieceSet ?? "merida";
      const isAssetPieceSet = typeof pieceSetRaw === "string" && pieceSetRaw.startsWith("assets/");
      // If user selects `assets/<name>` but doesn't specify base URL, prefer built-in package assets.
      // Note: requires calling `register_builtin_piece_assets()` at app compile/import time.
      const piecesBaseUrl = options?.piecesBaseUrl ?? (isAssetPieceSet ? "/external/reflex_chessboard/pieces" : "/pieces");
      const pieceSet = isAssetPieceSet ? pieceSetRaw.slice("assets/".length) : pieceSetRaw;
      let boardSize = options?.boardSize; // number(px) or string (e.g. "420px")
      const responsive = !!options?.responsive;
      // In responsive mode we size via container; we only use responsiveSize to force a remount (see `boardKey`).
      if (responsive) {
        boardSize = undefined;
      }

      // Theme defaults (user options can override).
      const themeDefaults = {};
      if (boardTheme === "gray") {
        themeDefaults.lightSquareStyle = { backgroundColor: "#e6e6e6" };
        themeDefaults.darkSquareStyle = { backgroundColor: "#666666" };
        themeDefaults.dropSquareStyle = { boxShadow: "inset 0 0 0 4px rgba(0, 150, 255, 0.55)" };
        themeDefaults.boardStyle = { borderRadius: "6px", boxShadow: "0 6px 18px rgba(0,0,0,0.18)" };
      }

      // Piece set defaults.
      if (pieceSet === "unicode") {
        themeDefaults.pieces = makeUnicodePieces();
      } else if (isAssetPieceSet && pieceSet) {
        // Load from app static assets, e.g. /pieces/merida/wK.svg
        themeDefaults.pieces = makeSvgAssetPieces(piecesBaseUrl, pieceSet);
      } else if (defaultPieces) {
        // "merida" / default: use library-provided SVG set (also avoids licensing issues on our side).
        themeDefaults.pieces = defaultPieces;
      }

      const themedOptions = { ...themeDefaults, ...(options || {}) };
      // Optional fixed size control: set boardStyle width/height (board is 100% by default).
      if (boardSize !== undefined && boardSize !== null) {
        const sizeValue = (typeof boardSize === "number") ? `${boardSize}px` : `${boardSize}`;
        themedOptions.boardStyle = {
          ...(themedOptions.boardStyle || {}),
          width: sizeValue,
          height: sizeValue,
        };
      }
      const baseSquareStyles = (options && options.squareStyles) ? options.squareStyles : {};
      const enableBuiltInHighlights = (options && options.enableBuiltInHighlights !== undefined)
        ? !!options.enableBuiltInHighlights
        : true;
      const highlightStyles = { ...baseSquareStyles };

      if (enableBuiltInHighlights) {
        // Highlight selected square.
        if (selectedSquare) {
          highlightStyles[selectedSquare] = {
            ...(highlightStyles[selectedSquare] || {}),
            boxShadow: "inset 0 0 0 4px rgba(255, 215, 0, 0.75)",
          };
        }

        // Highlight last move squares.
        if (lastMove?.from) {
          highlightStyles[lastMove.from] = {
            ...(highlightStyles[lastMove.from] || {}),
            boxShadow: "inset 0 0 0 4px rgba(0, 200, 0, 0.55)",
          };
        }
        if (lastMove?.to) {
          highlightStyles[lastMove.to] = {
            ...(highlightStyles[lastMove.to] || {}),
            boxShadow: "inset 0 0 0 4px rgba(0, 200, 0, 0.55)",
          };
        }
      }

      return {
        ...themedOptions,
        id,
        // react-chessboard expects a FEN string or position object; avoid "start" sentinel.
        position: (localFen === "start") ? (startFenRef.current || localFen) : localFen,
        onPieceDrop: onPieceDrop,
        onSquareClick: onSquareClick,
        onSquareMouseDown: onSquareMouseDown,
        onPieceClick: onPieceClick,
        squareStyles: highlightStyles,
        onArrowsChange: onArrowsChangeInternal,
      };
    }, [options, localFen, reactId, selectedSquare, lastMove, onSquareClick, onSquareMouseDown, onPieceClick, onArrowsChangeInternal, responsiveSize]);

    // IMPORTANT: react-chessboard's drag math relies on measured board dimensions.
    // On resize, it may keep stale measurements; remounting forces a fresh measurement.
    const boardKey = (options && options.responsive)
      ? `${mergedOptions.id}-${responsiveSize || 0}`
      : mergedOptions.id;

    return jsx("div", {
      ref: containerRef,
      style: { width: "100%", height: "100%" },
      children: jsx(ChessboardComp, { key: boardKey, options: mergedOptions }),
    });
  };
});
"""


chessboard = Chessboard.create
