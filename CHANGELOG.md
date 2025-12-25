# Changelog

Все заметные изменения в этом проекте документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
а версияция следует [SemVer](https://semver.org/lang/ru/).

## [0.1.0] - 2025-12-25

### Added
- **Компонент `Chessboard` для Reflex** (shim на базе `react-chessboard` + `chess.js`) с клиентской загрузкой зависимостей (без импорта `.jsx` из `/public`).
- **Drag & Drop** с проверкой легальности ходов через `chess.js` на клиенте и событием `on_move(payload)` на Python.
- **Click-to-move** (двумя кликами) на клиенте.
- **Аннотации**:
  - сервер → клиент: `options.squareStyles`, `options.arrows`
  - клиент → сервер: `on_arrows_change(payload)` при рисовании стрелок (если включено `allowDrawingArrows`)
- **Темы/стили**:
  - `options.boardTheme` (пресеты цветов)
  - `options.pieceSet` (`merida`, `unicode`, `assets/<name>`) и `options.piecesBaseUrl`
  - `options.showNotation`
- **Responsive режим** (`options.responsive`) на базе `ResizeObserver` + ремоунт по `key` для стабильности DnD после изменения размеров.
- **Событие `on_resize(payload)`** для синхронизации размера контейнера (используется в демо для обновления input `Board size`).
- **Демо-приложение** `chessboard_demo` с управлением темой, фигурами, ориентацией, аннотациями и ресайзом мышью.
- Базовая упаковка/CI: `ruff`, `pytest`, `python -m build`, `twine check`.

### Fixed
- Устранены проблемы с Vite (запрет импорта `.jsx` из `/public`) за счёт инъекции shim-кода через `_get_custom_code()`.
- Исправлены проблемы с DnD и координатами после ресайза (ремоунт chessboard по `key`).
- Устранён dev-loop рестартов из-за битых symlink’ов в `assets/external` (очистка + рекомендации).

## [0.1.1] - 2025-12-25

### Fixed
- Исправлен click-to-move в некоторых окружениях: выбор фигуры больше не “снимается” на отпускании кнопки мыши из-за последовательности `onSquareMouseDown` → `onSquareClick`.

## [0.1.4] - 2025-12-25

### Added
- Встроенные SVG-наборы фигур в пакете: `merida`, `cburnett`, `maestro`, `pirouetti`.
- API для встроенных ассетов: `list_builtin_piece_sets()`, `builtin_pieces_base_url()`, `register_builtin_piece_assets()`, `builtin_piece_options()`.

### Changed
- Если выбран `pieceSet="assets/<name>"` и `piecesBaseUrl` не задан, по умолчанию используется `"/external/reflex_chessboard/pieces"`.

### Fixed
- `register_builtin_piece_assets()` теперь:
  - создаёт директорию назначения `assets/external/reflex_chessboard/pieces` при необходимости
  - выдаёт более понятные ошибки (например при отсутствии SVG в установленном пакете)

