> **Language / Мова:** English | [Українська](NOTES.md)

# Project Notes

**Fork of [SergeySatskiy/codimension](https://github.com/SergeySatskiy/codimension).** The original is unmaintained.  
**Active fork:** https://github.com/sesquicadaver/codimension

## Installation for Users

The only supported method is cloning the repository and running `pip install -e .` in a venv.  
See [doc/en/INSTALL.md](doc/en/INSTALL.md) (Ukrainian: [doc/INSTALL.md](doc/INSTALL.md)).
IDE Help: [doc/user/index.md](doc/user/index.md).

`pip install codimension` from PyPI installs the **outdated upstream version (2020)**, not this fork.

## Fork Extensions

- `excludeFromAnalysis`, venv auto-exclusion from analysis
- Generate requirements file; **VENV… / Update VENV…** (T140); status-bar **Env:** (T141)
- Plugins: ruff, mypy, pytest, coverage, bandit, pip-audit, git
- Debugger watchpoints, greenlet trace; offscreen e2e + nightly full-IDE smoke

## AI (experimental)

**Options → Enable AI (experimental)** / **AI settings…**. Editor context menu → **AI**.
Flag `ai_ui` in `~/.codimension3/feature_flags.json`; override: `CDM_AI_UI=1`.
Backend is offline for now (no LLM). After update: `pip install -e .` and restart.

## pylint / wrapt on Python 3.11+

`cdmpylintplugin` pulls `pylint==2.5.3` → `astroid==2.5` → `wrapt<1.13`.
`constraints.txt` keeps `wrapt==1.12.1` so `pip install -c constraints.txt`
resolves; that build imports removed `inspect.formatargspec` and fails on 3.11+.
After install into the IDE venv:

```bash
.venv/bin/pip install 'wrapt>=1.14' --no-deps
```

(expected conflict with the astroid pin; `python -m pylint` then works).

---

# How to prepare a release (maintainers)

PyPI release is **optional** and is not the primary delivery method for the fork. If a tagged release is needed:

## Prepare the pypi config file `~/.pypirc`

```
[distutils]
index-servers =
  pypi
  pypitest

[pypi]
repository=https://pypi.python.org/pypi
username=<user>
password=<password>

[pypitest]
repository=https://test.pypi.org/legacy/
username=<user>
password=<password>
```

**Note:** Change permissions: `chmod 600 ~/.pypirc`

## Release Steps

1. Update ChangeLog
2. Make sure git clone is clean
3. Edit `codimension/cdmverspec.py` setting the new ``version`` and, if needed,
   ``release_channel`` (``stable`` / ``beta`` / ``dev``; R171 — still one version).
   Publish a GitHub Release with a PEP 440 tag (``vX.Y.Z``) and a wheel/sdist
   plus SHA-256 (API digest or ``*.sha256`` / ``SHA256SUMS``) so Help → Check for
   updates can verify a cache download (R172–R173); apply/install remains R180.
   Experimental AI UI: persistent flag ``ai_ui`` or env ``CDM_AI_UI`` (R174).
   Safe-mode IDE: ``codimension --safe-mode`` or ``CDM_SAFE_MODE=1`` (R175).
4. Build (recommended):

```shell
pip install build
python -m build
```

5. Verify `dist/` has required files
6. Upload to pypitest (optional):

```shell
pip install twine
twine upload -r pypitest dist/*
```

7. Test from pypitest (if step 6 was used)
8. **Automatic release:** create a tag — workflow `.github/workflows/release.yml` will build and upload to PyPI:

```shell
git tag -a v4.11.0 -m "Release 4.11.0"
git push --tags
```

Requires GitHub Secret `PYPI_API_TOKEN` (token from pypi.org, format pypi-xxx).

9. **Manual upload:** if not using the workflow:

```shell
twine upload dist/*
```

10. Publish release on GitHub: https://github.com/sesquicadaver/codimension/releases

## Development

```shell
pip install -r requirements.txt
pip install -e .
```

## Links

- [Peter Downs — PyPI](http://peterdowns.com/posts/first-time-with-pypi.html)
- [Ewen Cheslack-Postava — packaging](https://ewencp.org/blog/a-brief-introduction-to-packaging-python/)
