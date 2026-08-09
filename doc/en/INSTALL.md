# Installing Codimension (fork)

> **Language / Мова:** English | [Українська](../INSTALL.md)

**Active repository:** https://github.com/sesquicadaver/codimension  
**Version:** 4.11.0  

This fork is **not** published to the PyPI project named `codimension`. Install from a GitHub checkout or a wheel built from this repository. `pip install codimension` on PyPI is upstream 4.9.1 (2020).

## Supported platforms

| Platform | Status |
| -------- | ------ |
| Linux | CI-tested (Ubuntu) |
| Windows | Unverified — no compatibility guarantee |
| macOS | Unverified — no compatibility guarantee |

## Python

- Verified in CI: **3.10, 3.11, 3.12, 3.13**
- Metadata `requires-python`: `>=3.10` (versions after 3.13 are not verified)

## End-user install (minimal)

```bash
git clone https://github.com/sesquicadaver/codimension.git
cd codimension
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
codimension
```

Dependencies: PyQt5 and runtime packages from `pyproject.toml`. Compilers such as `g++` / `libpcre` for native parser extensions are **not** required — pure-Python AST parsers are used.

## Analyzer plugins (optional)

Plugin UI is bundled, but tools (Ruff, Mypy, Pytest, Coverage, Bandit, pip-audit) are optional extras:

```bash
python -m pip install ".[tools,lint,test,security]"
```

## Development / CI

```bash
python -m pip install -e ".[tools,lint,test,security]"
# or the full convenience snapshot (runtime + lint/test/security):
python -m pip install -r requirements.txt
python -m pip install -e .
# Python 3.11+: pylint stack needs a newer wrapt than astroid 2.5 allows
python -m pip install 'wrapt>=1.14' --no-deps
```

`requirements.txt` is **not** a minimal end-user install; it is the full local/CI environment.

## Next

- In-app user guide: [../user/index.md](../user/index.md)
- Repository: https://github.com/sesquicadaver/codimension
