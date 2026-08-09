# Codimension

> **Мова / Language:** Українська | [English](README.en.md)

[![CI](https://github.com/sesquicadaver/codimension/actions/workflows/ci.yml/badge.svg)](https://github.com/sesquicadaver/codimension/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GPL%20v3-green.svg)](LICENSE)

**Експериментальна Python IDE** з текстовим редактором і **діаграмою потоку керування**, що оновлюється під час редагування. Версія форку: **4.11.0**.

Активний форк [SergeySatskiy/codimension](https://github.com/SergeySatskiy/codimension). Останній commit upstream `master`: **19 серпня 2022**. Пакет `pip install codimension` на PyPI — upstream **4.9.1** (2020), не цей репозиторій. Цей форк у проєкт PyPI `codimension` не опублікований.

## Що перевірено зараз

- Редагування Python і синхронізована control-flow діаграма
- Діаграми імпортів / класів / залежностей; dead code, складність, pyflakes у редакторі
- Проєкти `.cdm3` (без автозавантаження останнього проєкту)
- Локальний Project VENV (Tools → **VENV…** / **Update VENV…**; status **Env:**)
- Pure-Python AST-парсери під compatibility-іменами `cdmpyparser` / `cdmcfparser` (C-extension не потрібен)
- UI плагінів у `cdmplugins/` (Ruff, Mypy, Pytest тощо потребують optional extras)
- Debugger (breakpoints, watchpoints); debugger session tests у CI
- Help → Check for updates (GitHub Releases; verified download у cache, без auto-apply)
- CI на **Ubuntu**: Ruff, format, Mypy, pytest matrix **Python 3.10–3.13**, wheel + `pip check`, Qt offscreen bootstrap smoke, `pip-audit`

## Обмеження

- Не production-ready IDE
- **Linux** — єдина CI-верифікована платформа; Windows / macOS — **unverified** (немає гарантій)
- Git-плагін — MVP; PR створюється через **GitHub REST API** (токен: `gh auth` → keyring → файл `0600`)
- Qt offscreen smoke у PR CI створює лише `QApplication` (не MainWindow / plugins)
- Full MainWindow smoke — weekly workflow, не PR-blocker
- Технічний борг аудиту закрито в [TODO_FIXME.md](TODO_FIXME.md); активна черга [ROADMAP.uk.md](ROADMAP.uk.md) порожня (відкладено R180–R182); safe-mode: `--safe-mode` / `CDM_SAFE_MODE=1`

## Вимоги

- Python **3.10–3.13** (саме цей діапазон у CI; відкритий діапазон без матриці не заявляємо)
- PyQt5
- Linux (primary)

## Встановлення (користувач)

```bash
git clone https://github.com/sesquicadaver/codimension.git
cd codimension
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
# або з кореня репо (venv + PYTHONPATH):
./scripts/run_codimension.sh
# optional: ./scripts/run_codimension.sh /path/to/project.cdm3
```

Плагіни аналізаторів (Ruff, Mypy, Pytest, …):

```bash
python -m pip install ".[tools,lint,test,security]"
```

Деталі: [doc/uk/README.md](doc/uk/README.md) → встановлення ([doc/INSTALL.md](doc/INSTALL.md)).

## Розробка

```bash
python -m pip install -e ".[tools,lint,test,security]"
# або convenience snapshot:
# python -m pip install -r requirements.txt && python -m pip install -e .
pytest tests/ -v
ruff check codimension cdmplugins
```

Чекліст PR: [CONTRIBUTING.md](CONTRIBUTING.md).

## Документація

| | |
| --- | --- |
| [doc/uk/README.md](doc/uk/README.md) | Український індекс |
| [doc/en/README.md](doc/en/README.md) | English index |
| [doc/BILINGUAL.md](doc/BILINGUAL.md) | Політика двомовності |
| [FORK.md](FORK.md) | Зміни форку |
| [TODO_FIXME.md](TODO_FIXME.md) | Відомі проблеми (внутрішній audit) |
| [ChangeLog](ChangeLog) | Історія змін |
| [doc/www/](doc/www/) | Локальне архівне дзеркало старого сайту |

## Related projects

- [CAN-MCP](https://github.com/sesquicadaver/CAN-MCP) — окремий headless static-analysis MCP; **не** інтегрований у Codimension.

## Ліцензія

GPL v3. Див. [FORK.md](FORK.md), [doc/LICENSE_COMPLIANCE.md](doc/LICENSE_COMPLIANCE.md).
