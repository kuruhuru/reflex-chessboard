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

### 2.3 Обёртка Reflex: NoSSRComponent + локальный React shim

Реализация делается через локальный React shim (JSX) и `rx.NoSSRComponent`, чтобы избежать SSR конфликтов.

## 3. Архитектура

### 3.1 Компоненты

#### A) Python wrapper (Reflex)

* `Chessboard(rx.NoSSRComponent)`
* подключает локальный shim через `rx.asset(..., shared=True)`
* определяет `lib_dependencies` (npm) с pinned версиями:

  * `react-chessboard@<pinned>`
  * `chess.js@<pinned>`

#### B) React shim (assets/*.jsx)

* экспортирует `ReflexChessboardShim`
* принимает props:

  * `fen` (string, `"start"` или FEN)
  * `options` (object; параметры react-chessboard, кроме onPieceDrop/position)
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
  AGENT_DEV_GUIDE.md
  src/
    reflex_chessboard/
      __init__.py
      chessboard.py
  assets/
    reflex_chessboard_shim.jsx
  chessboard_demo/
    rxconfig.py
    chessboard_demo/
      __init__.py
      chessboard_demo.py      # содержит app = rx.App()
      pages/
        index.py
  tests/
    test_imports.py
  package.json (если нужен для локальных JS тестов)
  .github/workflows/ci.yml
```

Примечание: В текущей ошибке запуска демо — Reflex не находит `app` в `chessboard_demo/chessboard_demo.py`. Исправить: обеспечить `app = rx.App()` в entry module демо.

## 5. План реализации (по шагам)

### Milestone 1 — “Board renders + DnD works + event to server”

1. Реализовать `assets/reflex_chessboard_shim.jsx`:

   * подключение `react-chessboard`
   * `chess.js` валидация onPieceDrop → boolean
   * синхронизация входного `fen` ↔ локального состояния
   * генерация payload и вызов `onMove(payload)`

2. Реализовать `src/reflex_chessboard/chessboard.py`:

   * `rx.NoSSRComponent`
   * `rx.asset()` → `library="$/public/<asset>"`
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
   * `uv publish` (на этапе релиза вручную)

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
