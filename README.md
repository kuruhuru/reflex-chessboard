# reflex-chessboard

Шахматная доска для **Reflex** на базе **react-chessboard** + **chess.js**.

Цели проекта:
- Drag & Drop с мгновенной проверкой легальности хода (без round-trip на сервер)
- Click-to-move (клики по клеткам)
- Аннотации “как в ChessBase”: стрелки + подсветка клеток (server↔client)
- Переиспользуемый пакет, устанавливаемый из PyPI

## Установка

```bash
pip install reflex-chessboard
```

## Быстрый старт

```python
import reflex as rx
from reflex_chessboard import (
    builtin_pieces_base_url,
    chessboard,
    list_builtin_piece_sets,
    register_builtin_piece_assets,
)


class State(rx.State):
    fen: str = "start"
    last_san: str = ""

    def on_move(self, payload: dict):
        # payload: {from,to,piece,promotion,fen,san}
        self.fen = payload.get("fen", self.fen)
        self.last_san = payload.get("san") or ""


def index():
    # (Опционально) если вы хотите использовать встроенные SVG-наборы из пакета:
    # - register_builtin_piece_assets() создаст shared assets в текущем приложении
    # - builtin_pieces_base_url() даст правильный baseUrl для img src
    register_builtin_piece_assets()
    _sets = list_builtin_piece_sets()
    return rx.vstack(
        chessboard(
            fen=State.fen,
            options={
                "allowDragging": True,
                "enableClickToMove": True,
                "showNotation": True,
                # Пример: используем встроенный набор "merida" из пакета:
                "pieceSet": "assets/merida",
                "piecesBaseUrl": builtin_pieces_base_url(),
            },
            on_move=State.on_move,
        ),
        rx.text(State.last_san),
        rx.code(State.fen),
    )


app = rx.App()
app.add_page(index, route="/")
```

Запуск:

```bash
cd chessboard_demo
uv run reflex run
```

## API (зафиксировано)

### Props

- **`fen: str`**: `"start"` или FEN.
- **`options: dict | None`**: Options API `react-chessboard` + расширения `reflex-chessboard`.

### Events

- **`on_move(payload: dict)`**: отправляется после успешного хода (DnD или click-to-move).
  - минимальные поля: `from`, `to`, `fen`, `san`, `promotion`, `piece`
- **`on_arrows_change(payload: dict)`** *(опционально)*: когда пользователь рисует стрелки.
  - формат: `{ "arrows": [...] }`
- **`on_resize(payload: dict)`** *(опционально)*: изменение размера контейнера в `responsive` режиме.
  - формат: `{ "size": 420 }` (в пикселях)

## Options: расширения `reflex-chessboard`

Это “наши” ключи, которые интерпретируются shim’ом:

- **`enableClickToMove: bool`** (default `True`): включить click-to-move.
- **`enableBuiltInHighlights: bool`** (default `True`): встроенные подсветки выбранной клетки и последнего хода.
- **`boardTheme: "default" | "gray"`**: пресеты цвета доски.
- **`boardSize: int | str`**: размер доски (например `420` или `"420px"`). Реализуется через `options.boardStyle.width/height`.
- **`responsive: bool`** (default `False`): подстраивать размер доски под контейнер (через `ResizeObserver`). Удобно для resizable контейнеров.  
  В этом режиме **`boardSize` игнорируется**, размер берётся из контейнера.
- **`pieceSet`**:
  - `"merida"`: встроенный SVG набор из `react-chessboard` (`defaultPieces`)
  - `"unicode"`: символы Unicode (без ассетов)
  - `"assets/<name>"`: SVG из статических ассетов приложения
- **`piecesBaseUrl: str`** (default `"/pieces"`): базовый URL для `assets/<name>`.
  - итоговый путь: `"{piecesBaseUrl}/{name}/{wK|bQ|...}.svg"`
  - если вы используете **встроенные наборы из пакета**, установите:
    - `piecesBaseUrl = builtin_pieces_base_url()`
    - и вызовите `register_builtin_piece_assets()`

## Встроенные SVG-наборы фигур (в пакете)

Пакет включает несколько популярных наборов: `merida`, `cburnett`, `maestro`, `pirouetti`.

API:
- **`list_builtin_piece_sets() -> list[str]`**: список доступных наборов
- **`builtin_pieces_base_url() -> str`**: base URL (обычно `"/external/reflex_chessboard/pieces"`)
- **`register_builtin_piece_assets(sets: Iterable[str] | None = None)`**: зарегистрировать наборы как shared assets

## Options: полезные ключи `react-chessboard` (pass-through)

Часто используемые:
- **`boardOrientation`**: `"white" | "black"`
- **`showNotation`**: `bool`
- **`squareStyles`**: `{ "e4": { "backgroundColor": "rgba(...)" }, ... }`
- **`arrows`**: `[{ "startSquare": "e2", "endSquare": "e4", "color": "#00aa00" }, ...]`
- **`allowDrawingArrows`**: `bool`
- **`arrowOptions`**: объект настроек стрелок

## Аннотации (рекомендуемый формат на Python)

Нормализованный формат (server-side):

```python
annotations = {
    "highlights": [{"square": "e4", "color": "rgba(255,215,0,0.35)"}],
    "arrows": [{"startSquare": "e2", "endSquare": "e4", "color": "#00aa00"}],
}
```

Далее адаптируйте в `options`:
- `highlights -> options["squareStyles"]`
- `arrows -> options["arrows"]`

## Важное про CSP

Reflex runtime в текущей версии использует `eval()` в `.web`. Если вы встраиваете приложение в окружение со строгим CSP (без `'unsafe-eval'`), это может ломать работу. Для PoC/демо используйте стандартный dev-режим Reflex.
