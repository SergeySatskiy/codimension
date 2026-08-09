# Встановлення Codimension (форк)

> **Мова / Language:** Українська | [English](en/INSTALL.md)

**Активний репозиторій:** https://github.com/sesquicadaver/codimension  
**Версія:** 4.11.0  

Цей форк **не** опублікований у PyPI-проєкті `codimension`. Встановлюйте з GitHub checkout або з wheel, зібраного з цього репозиторію. `pip install codimension` на PyPI — upstream 4.9.1 (2020).

## Підтримувані платформи

| Платформа | Статус |
| --------- | ------ |
| Linux | CI-tested (Ubuntu) |
| Windows | Unverified — немає гарантій |
| macOS | Unverified — немає гарантій |

## Python

- Перевірено в CI: **3.10, 3.11, 3.12, 3.13**
- `requires-python`: `>=3.10` у metadata (версії після 3.13 не верифіковані)

## Користувацьке встановлення (мінімум)

```bash
git clone https://github.com/sesquicadaver/codimension.git
cd codimension
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
codimension
```

Залежності: PyQt5 та runtime-пакети з `pyproject.toml`. Компілятори `g++` / `libpcre` для native parser extensions **не потрібні** — використовуються pure-Python AST parsers.

## Плагіни аналізаторів (optional)

UI плагінів bundled, але інструменти (Ruff, Mypy, Pytest, Coverage, Bandit, pip-audit) — optional extras:

```bash
python -m pip install ".[tools,lint,test,security]"
```

## Development / CI

```bash
python -m pip install -e ".[tools,lint,test,security]"
# або повний convenience snapshot (runtime + lint/test/security):
python -m pip install -r requirements.txt
python -m pip install -e .
# Python 3.11+: pylint stack needs a newer wrapt than astroid 2.5 allows
python -m pip install 'wrapt>=1.14' --no-deps
```

`requirements.txt` — **не** мінімальний користувацький install; це full local/CI environment.

## Далі

- Користувацька довідка IDE: [user/index.md](user/index.md)
- Репозиторій: https://github.com/sesquicadaver/codimension
