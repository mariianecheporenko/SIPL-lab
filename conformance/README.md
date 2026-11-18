# SIPL Conformance Suite (`CORE-06`)

Незалежний набір тестів для перевірки відповідності будь-якої реалізації специфікації мови SIPL.

## Контракт перевірюваної реалізації
Команда, передана через `--cmd <command>`, має підтримувати виклики:
1. `<command> parse <file.sipl>` — виводить канонічний JSON AST (поле `span` ігнорується при порівнянні) і повертає код виходу `0`.
2. `<command> run <file.sipl> --json [--max-steps N]` — виводить JSON із полем `"final_state"` і повертає `0` для валідних програм або ненульовий код виходу й тип помилки (`syntax` / `runtime`) для невалідних.

## Формат `cases.json`
- `id`: ідентифікатор кейсу;
- `description`: опис перевірки;
- `source`: вихідний код SIPL;
- `expect_valid`: `true` або `false`;
- `expected_ast`: очікуване JSON-дерево AST без полів `span` (для валідних програм);
- `expected_state`: очікуваний стан пам'яті змінних (для валідних програм);
- `error_kind`: `"syntax"` або `"runtime"` (для невалідних програм);
- `max_steps`: опційний ліміт кроків інтерпретації.

## Запуск
```bash
python -O conformance/run_conformance.py --cmd "sipl"