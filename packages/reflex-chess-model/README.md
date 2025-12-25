# reflex-chess-model

Общий контракт данных для chess-пакетов: `PackedGameTree v1` + валидация и утилиты.

## API (MVP)

- `validate_tree(tree) -> None`
- `get_node(tree, node_id)`
- `is_root(node_id) -> bool`


