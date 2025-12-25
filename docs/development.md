# Reflex Chessboard (reflex-chessboard) — Agent Development Guide

## 1. Цель проекта

Реализовать open-source библиотеку `reflex-chessboard` для Reflex (Python), предоставляющую компонент шахматной доски с:

1. **Drag & Drop** перемещением фигур (DnD)
2. поддержкой **click-to-move** (опционально, но желательно)
3. базовой инфраструктурой для **аннотаций “как в ChessBase”**:

   * стрелки (drawing + программный рендер)
   * подсветки квадратов
   * расширяемость под кружки/маркерные оверлеи

Проект должен быть:

* публикуемым как Python пакет (uv, pyproject.toml)
* с демо-приложением (Reflex app) внутри репозитория
* с документацией и тестами (CI)

Репозиторий: `https://github.com/kuruhuru/reflex-chessboard`

## 2. Выбранный стек и мотивация

### 2.1 Доска: react-chessboard

Выбрана библиотека **react-chessboard** (MIT), так как:

* это уже React-компонент → проще оборачивать в Reflex
* есть готовая поддержка DnD и стрелок/стилей через options API

### 2.2 Валидация ходов для DnD: chess.js в браузере

Проблема: `react-chessboard` ожидает, что `onPieceDrop` синхронно вернёт `boolean` (принять/отклонить drop). Reflex server events не могут вернуть значение синхронно.

Решение:

* в браузере держим `Chess` из `chess.js`
* `onPieceDrop` проверяет ход локально, синхронно возвращает `true/false`
* при успешном ходе shim:

  * обновляет локальный FEN
  * отправляет событие в Reflex (`on_move(payload)`) асинхронно

Это обеспечивает:

* правильный UX (нелегальные ходы отклоняются сразу, без “отката”)
* стабильность (нет зависимостей от latency сервера)

### 2.3 Обёртка Reflex: локальный React shim через injected custom code (без импортов из /public)

Реализация делается через injected shim-код (JS) внутри Python-компонента и `ClientSide(async () => import(...))`, чтобы:

* избежать SSR конфликтов
* не импортировать `.jsx` из `/public` (Vite это запрещает)

## 3. Архитектура

### 3.1 Компоненты

#### A) Python wrapper (Reflex)

* `Chessboard(rx.Component)`
* shim-код встраивается через `_get_custom_code()` (а не через импорт `.jsx` из `/public`/`assets`)
* определяет `lib_dependencies` (npm) с pinned версиями:

  * `react-chessboard@<pinned>`
  * `chess.js@<pinned>`

#### B) React shim (встроенный JS shim)

* определяет `ReflexChessboardShim` через `ClientSide(...)`
* принимает props:

  * `fen` (string, `"start"` или FEN)
  * `options` (object; параметры react-chessboard Options API + наши расширения)
  * `onMove` (callback; Reflex event handler)
* внутри:

  * держит `chessRef = new Chess()`
  * синхронизирует chessRef при изменениях fen от сервера
  * реализует `onPieceDrop` с локальной валидацией, возвращая boolean синхронно
  * обновляет локальный fen (`position`) и вызывает `onMove(payload)` после успешного хода

### 3.2 Contract/API

#### Props (Python → React)

* `fen: str = "start"`
* `options: dict | None`

  * прокидываем в react-chessboard options
  * на старте нужны, минимум:

    * `allowDragging: True/False`
    * `arePiecesDraggable: True/False`
    * `allowDrawingArrows: True/False`
    * `arrows: [...]` (для программных стрелок)
    * `squareStyles: {...}` (подсветки)

#### Events (React → Python)

* `on_move(payload: dict)`

  * payload поля (минимум):

    * `from: str` (e.g. "e2")
    * `to: str` (e.g. "e4")
    * `piece: str` (формат react-chessboard, например "wP"/"bN" — уточнить по факту)
    * `promotion: str | null` ("q"/"r"/"b"/"n")
    * `fen: str` (новый FEN после хода)
    * `san: str | null` (SAN из chess.js если доступен)

### 3.3 Поведение промоушена

MVP: автоматический promotion в ферзя (`q`).
Дальше: добавить UI выбора фигуры без ломки API (через отдельный event/prop).

### 3.4 Аннотации

MVP:

* стрелки: включить `allowDrawingArrows` в `options` и обработку изменения стрелок (если доступно) либо реализовать хранение стрелок в state с отдельными событиями позже.
* подсветки: через `squareStyles`

Важно: не “зашивать” формат аннотаций только под одну библиотеку. В Python держать нормализованный формат:

```python
annotations = {
  "arrows": [{"from": "e2", "to": "e4", "color": "#00aa00"}],
  "highlights": [{"square": "e4", "style": {...}}],
}
```

и адаптировать в shim/props.

## 4. Структура репозитория (целевое состояние)

Рекомендуемая структура (пример):

```
reflex-chessboard/
  pyproject.toml
  README.md
  CHANGELOG.md
  docs/
    development.md
  chessboard_demo/
    rxconfig.py
    chessboard_demo/
      __init__.py
      chessboard_demo.py      # содержит app = rx.App()
  custom_components/
    reflex_chessboard/
      __init__.py
      chessboard.py
      py.typed
      pieces/
        merida/*.svg
        cburnett/*.svg
        maestro/*.svg
        pirouetti/*.svg
  tests/
    test_imports.py
  package.json (если нужен для локальных JS тестов)
  .github/workflows/ci.yml
```

Примечание: отдельного `reflex_chessboard_shim.jsx` в ассетах больше нет — shim инжектится через `_get_custom_code()`.

### 4.1 Встроенные SVG-наборы фигур (в пакете)

Пакет включает несколько популярных SVG-наборов фигур: `merida`, `cburnett`, `maestro`, `pirouetti`.

Чтобы использовать их в приложении:

- вызовите `register_builtin_piece_assets()` (создаёт shared assets в текущем Reflex-приложении)
- установите:
  - `options["pieceSet"] = "assets/<name>"`
  - `options["piecesBaseUrl"] = builtin_pieces_base_url()` (обычно `"/external/reflex_chessboard/pieces"`)

API:
- `list_builtin_piece_sets() -> list[str]`
- `builtin_pieces_base_url() -> str`
- `register_builtin_piece_assets(sets: Iterable[str] | None = None) -> None`

## 5. План реализации (по шагам)

### Milestone 1 — “Board renders + DnD works + event to server”

1. Реализовать встроенный shim (JS) в компоненте:

   * подключение `react-chessboard`
   * `chess.js` валидация onPieceDrop → boolean
   * синхронизация входного `fen` ↔ локального состояния
   * генерация payload и вызов `onMove(payload)`

2. Реализовать `custom_components/reflex_chessboard/chessboard.py`:

   * `rx.Component` + injected shim code (`_get_custom_code`)
   * `tag = "ReflexChessboardShim"`
   * `lib_dependencies` pinned
   * props + event `on_move`

3. Обновить `__init__.py` для корректного экспорта:

   * `from .chessboard import chessboard, Chessboard`

4. Демо-приложение:

   * `chessboard_demo/chessboard_demo.py` содержит `app = rx.App()`
   * index page:

     * рендер `chessboard(fen=State.fen, options={...}, on_move=State.on_move)`
     * вывод текущего fen и последнего SAN
   * обеспечить запуск:

     * `cd chessboard_demo && uv run reflex run`

Критерии готовности:

* доска отображается
* DnD: легальные ходы принимаются, нелегальные отклоняются
* `State.fen` обновляется

Статус: ✅ выполнено

---

### Milestone 2 — “Click-to-move + basic annotations”

1. Click-to-move:

   * в State держать `selected_square`
   * на клик по квадрату:

     * если ничего не выбрано → выбрать
     * если выбрано → попытаться сделать ход (через серверный python-chess или через “клиентский” chess.js подход)
   * предпочтительно: reuse chess.js на клиенте для единообразия и мгновенности

2. Аннотации:

   * подсветки квадратов: `squareStyles`
   * стрелки:

     * включить `allowDrawingArrows: True`
     * если react-chessboard предоставляет событие изменения стрелок (проверить по факту версии) — прокинуть как `on_arrows_change`
     * если нет — минимум обеспечить программный рендер стрелок через `options.arrows`

Критерии готовности:

* кликами можно ходить без DnD
* подсветка выбранного квадрата и последнего хода
* можно отобразить стрелку программно через state

Статус: ✅ выполнено (включая `on_arrows_change`)

---

### Milestone 3 — “Packaging + docs + CI”

1. README:

   * установка (`uv add reflex-chessboard`)
   * минимальный пример кода
   * описание API props/events
   * примеры аннотаций

2. CI:

   * Python lint/format (ruff)
   * typecheck (pyright/mypy по выбору)
   * unit tests (pytest)
   * опционально: e2e playwright для demo (см. ниже)

3. Релизный процесс:

   * версия в pyproject
   * `uv build`
   * публикация в PyPI (см. Milestone 4)

Статус: ✅ выполнено (CI: ruff/pytest/build/twine check)

---

### Milestone 4 — “Автопубликация в PyPI по тегу версии”

Цель: стандартный релиз-процесс “как обычно”: коммит → tag `vX.Y.Z` → GitHub Actions собирает и публикует пакет.

1. Триггер:

   * push тега вида `v*` (например `v0.1.2`)

2. Пайплайн:

   * checkout
   * setup Python
   * `uv sync --group dev`
   * `ruff` + `pytest`
   * `python -m build`
   * публикация в PyPI

3. Способ публикации:

   * предпочтительно: **Trusted Publishing** (PyPI ↔ GitHub OIDC, без токенов)
   * альтернатива: секрет `PYPI_API_TOKEN` и `twine upload`

Критерии готовности:

* при push тега `vX.Y.Z` пакет появляется в PyPI с корректной версией
* workflow не требует ручных шагов (кроме создания версии/tag)

## 6. Тестирование

### 6.1 Python unit tests (обязательные)

Цель: гарантировать, что пакет импортируется и компонент объявлен корректно.

Минимум:

* `tests/test_imports.py`:

  * `import reflex_chessboard`
  * `from reflex_chessboard import chessboard, Chessboard`
  * проверка, что `Chessboard.tag` и `Chessboard.library` заданы (не “Fill-Me”)
  * проверка, что `lib_dependencies` содержит pinned зависимости

Дополнительно:

* тест на сериализацию options (простые dict)
* тест на сигнатуру event triggers (наличие `on_move`)

### 6.2 JS unit tests для shim (желательно)

Если добавляем Node toolchain для тестов:

* Vitest + React Testing Library
* тесты:

  * `onPieceDrop` возвращает false для нелегального хода (например, pawn назад)
  * `onPieceDrop` возвращает true и вызывает `onMove` с новым fen для легального хода
  * синхронизация входного `fen` корректно обновляет локальный `position`

Если JS unit tests не делаем — компенсировать e2e.

### 6.3 E2E (рекомендуется для уверенности)

Playwright по demo-приложению:

* сценарий:

  * открыть страницу
  * выполнить DnD хода (e2→e4) через mouse events
  * проверить, что fen изменился (текст на странице)
* дополнительные проверки:

  * нелегальный ход не меняет fen

Плюс:

* это проверяет и интеграцию Reflex ↔ React shim ↔ npm deps.

## 7. Стандарты качества и ограничения

* Пиновать версии npm-зависимостей (устойчивость в проде).
* Не полагаться на серверный round-trip для решения “принять drop или нет”.
* API компонента держать максимально узким и стабильным:

  * `fen`, `options`, `on_move` — обязательный минимум
  * остальное добавлять аддитивно, без breaking changes
* Не пытаться сразу “ChessBase 100%”; сделать основу аннотаций и расширяемость.

## 8. Команды разработки (uv)

* установка зависимостей:

  * `uv sync`
* запуск демо:

  * `cd chessboard_demo && uv run reflex run`
* тесты:

  * `uv run pytest`
* линтер:

  * `uv run ruff check .`
* формат:

  * `uv run ruff format .`

## 9. Definition of Done (первый релиз)

* `pip install reflex-chessboard` (локально через uv) работает
* демо запускается
* DnD работает с локальной валидацией
* событие `on_move` обновляет FEN
* README содержит установку + пример
* CI зелёный
* есть хотя бы базовые тесты (Python) и предпочтительно e2e

---

## 10. Статус по факту (актуализация)

### 10.1 Что уже сделано (PoC / Milestone 1 — выполнен)

#### Компонент

- **Рабочая интеграция `react-chessboard@5.8.6` + `chess.js@1.4.0`**.
- **DnD**: локальная синхронная валидация хода через `chess.js` и мгновенное отклонение нелегальных ходов.
- **Event → сервер**: событие `on_move(payload)` отправляется в Reflex, payload включает минимум `{from,to,promotion,fen,san,...}`.
- **Server → client sync**: входной `fen` синхронизирует позицию на доске; добавлены server-side действия в демо (reset/preset/flip orientation) для проверки “в обе стороны”.

#### Важные технические нюансы, выявленные в процессе

- **react-chessboard использует Options API**: `Chessboard` принимает проп `options`, а `onPieceDrop` имеет сигнатуру `onPieceDrop({piece, sourceSquare, targetSquare}) => boolean`.
- **Нельзя импортировать локальный `.jsx` модулем из `/public` в Vite**. Поэтому текущий shim **не подключается как asset**, а **инжектится через `_get_custom_code()`** и грузит npm зависимости на клиенте (`ClientSide(async () => import(...))`).
- **Reflex event args**: чтобы обработчик принимал payload, поле события объявляется через `Annotated[rx.EventHandler, lambda payload: [payload]]`.
- **CSP**: текущий runtime Reflex в `.web` использует `eval()`; строгий CSP без `'unsafe-eval'` может ломать работу приложения (важно для продакшн-окружений/встраивания).

#### Демо

- Демо запускается, доска отображается, DnD работает.
- В демо отображаются FEN/последний ход/последний payload, и есть server-side кнопки:
  - reset позиции
  - установка preset FEN
  - flip board orientation

#### Базовые тесты

- Добавлен минимальный `pytest` тест импорта/контракта компонента.

### 10.2 Что предстоит (следующие крупные этапы)

#### Milestone 2 — Click-to-move + basic annotations

- **Click-to-move**:
  - хранить выбранный квадрат на клиенте (предпочтительно) или на сервере
  - использовать `options.onSquareClick` + локальную валидацию через `chess.js` (чтобы UX был мгновенным, как и в DnD)
- **Подсветки**:
  - выбранный квадрат
  - последний ход (from/to)
  - через `options.squareStyles`
- **Стрелки**:
  - включить `options.allowDrawingArrows`
  - добавить `options.onArrowsChange` → event `on_arrows_change` (если хотим фиксировать пользовательские стрелки)
  - плюс программный рендер через `options.arrows`

#### Milestone 3 — Packaging + docs + CI

- **README**: установка, минимальный пример, API (props/events), примеры annotations.
- **CI**: ruff + pytest (+ опционально e2e).
- **E2E**: Playwright по демо (DnD e2→e4, проверка изменения FEN).

### 10.3 Предлагаемые следующие шаги (конкретный список)

1. **Стабилизировать публичный API** компонента (Python): `fen`, `options`, `on_move` + добавить (аддитивно) `on_arrows_change` и/или `on_square_click`.
2. **Click-to-move на клиенте** через `options.onSquareClick` + `chess.js` (без round-trip).
3. **Подсветки**: selected + last move через `squareStyles` (MVP).
4. **Стрелки**: `allowDrawingArrows` + проброс `onArrowsChange` в Reflex (MVP).
5. **Документация**: обновить README под реальный Options API и current shim approach (инжект через custom code).
6. **CI**: добавить workflow с `uv sync` + `pytest`.
