# -*- coding: utf-8 -*-
"""In-app Help must resolve to the user guide and stay within end-user docs."""

from __future__ import annotations

import os
import re
from collections import deque
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_INDEX = REPO_ROOT / "doc" / "user" / "index.md"

LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")
# Paths that must not appear in the Help markdown link graph.
NON_USER_NAME_PARTS = (
    "roadmap",
    "todo_fixme",
    "living-specification",
    "fork.md",
    "fork.en.md",
    "notes.md",
    "notes.en.md",
    "contributing",
    "bilingual",
    "github-integration-plan",
    "plugins-implementation-plan",
    "git-github-plugin-plan",
    ".omx",
    ".cursor",
)


def _normalize_target(raw: str) -> str:
    text = raw.strip()
    if text.startswith("<") and ">" in text:
        text = text[1 : text.index(">")]
    if ' "' in text:
        text = text.split(' "', 1)[0]
    elif " '" in text:
        text = text.split(" '", 1)[0]
    if "#" in text:
        text = text.split("#", 1)[0]
    return text.strip()


def _walk_product_markdown(start: Path) -> set[Path]:
    """BFS relative markdown closure from the product Help entry."""
    seen: set[Path] = set()
    queue: deque[Path] = deque([start.resolve()])
    while queue:
        path = queue.popleft()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        text = path.read_text(encoding="utf-8")
        for _label, target in LINK_RE.findall(text):
            rel = _normalize_target(target)
            if not rel or rel.startswith(("http://", "https://", "mailto:")):
                continue
            candidate = (path.parent / rel).resolve()
            if candidate.suffix.lower() == ".md" and REPO_ROOT in candidate.parents:
                queue.append(candidate)
    return seen


def test_resolve_product_help_index_points_to_user_guide():
    from utils.embedded_docs import resolve_product_help_index

    path = resolve_product_help_index()
    assert path is not None
    assert os.path.basename(path) == "index.md"
    assert os.path.basename(os.path.dirname(path)) == "user"


def test_resolve_product_help_index_ignores_generic_index(tmp_path, monkeypatch):
    """Fail-closed: a lone doc/index.md must not become Help."""
    from utils import embedded_docs as ed

    fake_root = tmp_path / "pkg"
    (fake_root / "doc").mkdir(parents=True)
    (fake_root / "doc" / "index.md").write_text("# stub\n", encoding="utf-8")
    monkeypatch.setattr(ed, "_candidate_doc_roots", lambda: [str(fake_root)])
    assert ed.resolve_product_help_index() is None

    user = fake_root / "doc" / "user"
    user.mkdir()
    (user / "index.md").write_text("# user\n", encoding="utf-8")
    assert ed.resolve_product_help_index() == str(user / "index.md")


def test_product_help_closure_stays_in_user_docs():
    assert USER_INDEX.is_file()
    closure = _walk_product_markdown(USER_INDEX)
    assert USER_INDEX.resolve() in closure
    offenders: list[str] = []
    for path in sorted(closure):
        rel = path.relative_to(REPO_ROOT).as_posix().lower()
        if any(part in rel for part in NON_USER_NAME_PARTS):
            offenders.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        for _label, target in LINK_RE.findall(text):
            norm = _normalize_target(target).lower()
            if any(part in norm for part in NON_USER_NAME_PARTS):
                offenders.append(f"{rel} -> {norm}")
    assert not offenders, "non-user docs reachable from Help:\n" + "\n".join(offenders)


def test_package_data_keeps_end_user_docs_only():
    from utils.package_docs_filter import is_product_package_doc

    doc_files = [p.name for p in (REPO_ROOT / "doc").iterdir() if p.is_file()]
    kept_root = [
        name for name in doc_files if name.endswith(".md") and is_product_package_doc("doc", name)
    ]
    assert "index.md" in kept_root
    assert "INSTALL.md" in kept_root
    assert "README.md" not in kept_root
    assert "github-integration-plan.md" not in kept_root

    plugin_files = [p.name for p in (REPO_ROOT / "doc" / "plugins").iterdir() if p.is_file()]
    kept_plugins = [
        name
        for name in plugin_files
        if name.endswith(".md") and is_product_package_doc("doc.plugins", name)
    ]
    assert "plugins.md" in kept_plugins
    assert "living-specification.md" not in kept_plugins
    assert not any("plan" in name.lower() for name in kept_plugins)
    assert is_product_package_doc("doc.user", "index.md")


def test_repo_has_no_codimension_project_file():
    assert not (REPO_ROOT / "codimension.cdm3").exists()
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "/codimension.cdm3" in gitignore


@pytest.mark.parametrize(
    "needle",
    [
        "/home/sesquicadaver/Projects/AdaptiveFC",
        "AdaptiveFC/.venv",
    ],
)
def test_no_host_specific_adaptivefc_hardcode(needle):
    text = (REPO_ROOT / "tests" / "test_process_env.py").read_text(encoding="utf-8")
    assert needle not in text
