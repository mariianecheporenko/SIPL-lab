# SIPL Language Toolkit

[![CI](https://github.com/mariianecheporenko/sipl-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/mariianecheporenko/sipl-lab/actions/workflows/ci.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Інструментарій для формальної мови програмування **SIPL** (*Simple Imperative Programming Language*), розроблений у межах курсу «Теорія програмування» (КНУ ім. Тараса Шевченка).

Реалізує повний цикл роботи з мовою: формальну LALR(1)-граматику, типізоване AST із позиціями у вихідному коді (`SourceSpan`), інтерпретатор із контролем нескінченних циклів, подієву модель трасування (`trace`), CLI з підтримкою JSON-режиму, візуалізацію дерев виводу та AST, а також незалежний conformance-набір тестів.

---

## Обрані завдання та заявлені бали

| ID | Модуль / Завдання | Бали | Статус |
|:---|:---|:---:|:---:|
| **CORE-01** | Формальна специфікація SIPL (Lark/EBNF, лексика, тести) | 0.5 | Реалізовано |
| **CORE-02** | Парсер та типізоване AST з точними позиціями (`SourceSpan`) | 1.5 | Реалізовано |
| **CORE-03** | Інтерпретатор SIPL (стан, оператори, ліміт кроків, покриття >80%) | 2.0 | Реалізовано |
| **CORE-04** | Подієва модель виконання та структурований trace | 1.0 | Реалізовано |
| **CORE-05** | CLI-інтерфейс (`check`, `parse`, `run`, `trace`, `visualize`, коди виходу) | 1.0 | Реалізовано |
| **CORE-06** | Conformance suite (незалежний runner, формат тестів, специфікація) | 1.0 | Реалізовано |
| **VIS-01** | Візуалізація дерева виводу / Parse Tree (Text, JSON, DOT, SVG) | 1.5 | Реалізовано |
| **VIS-02** | Візуалізація AST та порівняння Parse Tree ↔ AST (інтерактивний HTML) | 1.0 | Реалізовано |
| **REL-01** | CI на GitHub Actions (lint, type-check, tests, coverage, clean venv build) | 0.5 | Реалізовано |
| **REL-02** | Релізний цикл (SemVer, теги, структурований `CHANGELOG.md`) | 0.5 | Реалізовано |
| **Разом** | | **10.5** | *(максимум за курс — 10.0)* |

---

## Структура проєкту

- `src/sipl/` — ядро пакета: граматика (`grammar/sipl.lark`), парсер, AST, інтерпретатор, трасування, CLI та рендерери візуалізації (`visualization/`).
- `conformance/` — незалежний тестовий набір (`cases.json`, `run_conformance.py`) для перевірки будь-якої реалізації SIPL CLI.
- `docs/` — план проєкту (`PLAN.md`) та JSON-схема виводу CLI (`json-schema.json`).
- `examples/` — приклади SIPL-програм (`parity.sipl`, `power.sipl`, `div.sipl`, `bad.sipl`).
- `tests/` — модульні та інтеграційні тести (`pytest`).

---

## Встановлення

Потрібен **Python 3.10+**.

```bash
git clone [https://github.com/mariianecheporenko/sipl-lab.git](https://github.com/mariianecheporenko/sipl-lab.git)
cd sipl-lab

python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
```
Після встановлення доступна команда sipl (або python -m sipl).
---

## Використання CLI
Усі 5 підкоманд підтримують уніфікований прапорець --json для інтеграції в інші інструменти.

Перевірка, парсинг, виконання та трасування
```bash
# Синтаксична валідація без виконання
sipl check examples/parity.sipl --json

# Побудова канонічного AST у форматі JSON
sipl parse examples/power.sipl --json

# Інтерпретація програми та вивід фінального стану змінних
sipl run examples/power.sipl --json
sipl run examples/power.sipl --max-steps 100

# Покроковий журнал виконання (зміна змінних, умови гілок і циклів)
sipl trace examples/parity.sipl --max-steps 1000
```
---

## Візуалізація дерев розбору та AST
Підтримуються формати text, dot, svg, json, а також інтерактивний html для порівняння Parse Tree ↔ AST:

```bash
# ASCII-дерево виводу в терміналі
sipl visualize examples/parity.sipl --kind parse --format text

# Експорт AST у векторний SVG
sipl visualize examples/parity.sipl --kind ast --format svg -o out/ast.svg

# Інтерактивне HTML-порівняння Parse Tree ↔ AST із синхронним підсвічуванням коду
sipl visualize examples/parity.sipl --kind compare --format html -o out/compare.html
```
---

## Коди завершення (Exit Codes)

0 — успішне виконання команди.

1 — синтаксична помилка розбору (SiplSyntaxError).

2 — помилка часу виконання (SiplError, звернення до неініціалізованої змінної, некоректні аргументи CLI).

3 — перевищено ліміт кроків виконання (ExecutionLimitError, спрацював захист від зациклення).

У разі помилки на stderr виводиться структурований JSON-об'єкт із діагностикою та позицією span (див. docs/json-schema.json).

---

## Специфікація синтаксису SIPL
Оператори: присвоювання (:=), послідовне виконання (;), розгалуження (if C then S1 else S2), цикл (while C do S), блок (begin S end), порожній оператор (skip).

Арифметичні вирази: цілі константи (включно з від'ємними літералами), змінні (A-Z), операції +, -, * зі стандартним пріоритетом і дужками (...).

Логічні умови: порівняння =, >, заперечення ~, строга диз'юнкція \/ (також підтримується |).

Лексика: ключові слова не склеюються з ідентифікаторами та числами.
---

## Тестування та перевірка якості
```bash
pytest --cov=sipl --cov-report=term-missing
ruff check src tests conformance
mypy src
python -O conformance/run_conformance.py --cmd "sipl"
```