# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2026  Codimension Team
# The license is described in the LICENSE file at the root directory.
#
# pylint: disable=C0305

"""Resolve the in-app Help documentation index (``doc/user/index.md``)."""

from __future__ import annotations

import importlib.util
import os.path
import sys


def _candidate_doc_roots() -> list[str]:
    """Return ordered filesystem roots that may contain ``doc/user/``.

    Prefer package-relative locations over ``sys.argv[0]`` (launcher path is
    often a venv ``bin/`` wrapper and is the least reliable root).
    """
    roots: list[str] = []
    here = os.path.dirname(os.path.abspath(__file__))
    # .../codimension/utils → package parent (editable: repo root)
    roots.append(os.path.dirname(os.path.dirname(here)))
    # .../site-packages/codimension/utils → site-packages (installed layout)
    roots.append(os.path.dirname(os.path.dirname(os.path.dirname(here))))

    try:
        spec = importlib.util.find_spec("doc")
    except (ImportError, AttributeError, ValueError):
        spec = None
    if spec is not None:
        locations = getattr(spec, "submodule_search_locations", None) or ()
        for loc in locations:
            if not loc or str(loc).startswith("__editable__"):
                continue
            abs_loc = os.path.abspath(str(loc))
            parent = os.path.dirname(abs_loc)
            if parent:
                roots.append(parent)
            roots.append(abs_loc)

    argv0 = sys.argv[0] if sys.argv else ""
    if argv0:
        roots.append(os.path.dirname(os.path.dirname(os.path.abspath(argv0))))

    seen: set[str] = set()
    unique: list[str] = []
    for root in roots:
        if root and root not in seen:
            seen.add(root)
            unique.append(root)
    return unique


def resolve_product_help_index() -> str | None:
    """Return absolute path to ``doc/user/index.md``, or None if missing.

    Fail-closed: only the user-guide index is accepted (no generic ``index.md``).
    """
    relative_candidates = ("doc/user/index.md", "user/index.md")
    for root in _candidate_doc_roots():
        for rel in relative_candidates:
            path = os.path.join(root, rel)
            if os.path.isfile(path):
                return path
    return None
