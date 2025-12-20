import React, { useEffect, useMemo, useRef, useState } from "react";
import { Chess } from "chess.js";
import { Chessboard } from "react-chessboard";

/**
 * ReflexChessboardShim
 * Props:
 * - fen: "start" | FEN string
 * - options: object (react-chessboard options, кроме onPieceDrop/position)
 * - onMove: function(payload) -> void  (Reflex event handler)
 */
export function ReflexChessboardShim(props) {
    const { fen, options, onMove } = props;

    const chessRef = useRef(null);
    const [localFen, setLocalFen] = useState(fen || "start");

    // Инициализация chess.js
    if (!chessRef.current) {
        chessRef.current = new Chess();
        if (fen && fen !== "start") {
            try {
                chessRef.current.load(fen);
            } catch {
                // если пришёл битый fen — оставляем старт
                chessRef.current.reset();
            }
        }
    }

    // Когда серверный fen меняется — синхронизируем фронт
    useEffect(() => {
        if (!fen) return;
        if (fen === localFen) return;

        try {
            if (fen === "start") chessRef.current.reset();
            else chessRef.current.load(fen);

            setLocalFen(fen);
        } catch {
            // игнорируем некорректный fen
        }
    }, [fen]);

    // Простейшая логика промоушена: всегда в ферзя.
    // В будущем можно сделать UI выбора и прокинуть callback.
    function inferPromotion(piece, targetSquare) {
        const isPawn = piece?.endsWith("P");
        if (!isPawn) return undefined;
        const rank = targetSquare?.[1];
        if (rank === "8" || rank === "1") return "q";
        return undefined;
    }

    function onPieceDrop(sourceSquare, targetSquare, piece) {
        if (!sourceSquare || !targetSquare) return false;

        const promotion = inferPromotion(piece, targetSquare);

        const move = {
            from: sourceSquare,
            to: targetSquare,
            promotion: promotion,
        };

        const result = chessRef.current.move(move);
        if (!result) {
            return false; // нелегальный ход — отклоняем синхронно
        }

        const newFen = chessRef.current.fen();
        setLocalFen(newFen);

        // Событие в Reflex: асинхронно, без влияния на возврат boolean
        if (onMove) {
            onMove({
                from: sourceSquare,
                to: targetSquare,
                piece: piece,
                promotion: promotion ?? null,
                fen: newFen,
                san: result.san ?? null,
            });
        }

        return true;
    }

    const mergedOptions = useMemo(() => {
        return {
            ...(options || {}),
            position: localFen,
            onPieceDrop: onPieceDrop,
        };
    }, [options, localFen]);

    return <Chessboard options={mergedOptions} />;
}
