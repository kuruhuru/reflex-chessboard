from __future__ import annotations
from typing import Annotated, Any, Dict, Optional
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
    options: Optional[Dict[str, Any]] = None

    # Events (React -> Python). Reflex will expose this to JS as `onMove`.
    # Provide an ArgsSpec so handlers can accept a payload dict, e.g. `def on_move(self, payload: dict): ...`
    on_move: Annotated[rx.EventHandler, lambda payload: [payload]]

    def add_imports(self):
        # Imports required for injected shim code.
        return {
            "react": [
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
  const ChessCtor =
    chessJsMod?.Chess ??
    chessJsMod?.default?.Chess ??
    chessJsMod?.default ??
    chessJsMod;

  return function ReflexChessboardShimInner(props) {
    const { fen, options, onMove } = props;

    const reactId = useId();
    const debug = (options && options.debug) ? true : false;
    const chessRef = useRef(null);
    const startFenRef = useRef(null);
    const [localFen, setLocalFen] = useState(fen || "start");

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

      const promotion = inferPromotion(sourceSquare, targetSquare);
      let result = null;
      try {
        result = chessRef.current.move({
          from: sourceSquare,
          to: targetSquare,
          promotion,
        });
      } catch (e) {
        console.error("[reflex-chessboard] chess.js move error", e, {
          sourceSquare,
          targetSquare,
          piece,
          promotion,
          fen: chessRef.current?.fen?.(),
        });
        return false;
      }

      if (!result) {
        console.warn("[reflex-chessboard] illegal move rejected", {
          sourceSquare,
          targetSquare,
          piece,
          promotion,
          fen: chessRef.current?.fen?.(),
        });
        return false;
      }

      const newFen = chessRef.current.fen();
      setLocalFen(newFen);

      if (onMove) {
        onMove({
          from: sourceSquare,
          to: targetSquare,
          piece: piece?.pieceType ?? null,
          promotion: promotion ?? null,
          fen: newFen,
          san: result.san ?? null,
        });
      }

      return true;
    }

    const mergedOptions = useMemo(() => {
      const id = (options && options.id) ? options.id : `reflex-chessboard-${reactId}`;
      return {
        ...(options || {}),
        id,
        // react-chessboard expects a FEN string or position object; avoid "start" sentinel.
        position: (localFen === "start") ? (startFenRef.current || localFen) : localFen,
        onPieceDrop: onPieceDrop,
      };
    }, [options, localFen, reactId]);

    return jsx(ChessboardComp, { options: mergedOptions });
  };
});
"""


chessboard = Chessboard.create
