# -*- coding: utf-8 -*-
#
# codimension - graphics python two-way code editor and analyzer
# Copyright (C) 2026  Codimension Team
# The license is described in the LICENSE file at the root directory.
#
# pylint: disable=C0305

"""Which documentation files belong in the installed package."""

from __future__ import annotations


def is_product_package_doc(package: str, file_name: str) -> bool:
    """Return True if ``file_name`` should ship with package ``package``."""
    lower = file_name.lower()
    if package == "doc":
        if file_name in ("README.md", "BILINGUAL.md", "github-integration-plan.md"):
            return False
        if "plan" in lower:
            return False
        return True
    if package == "doc.user":
        return True
    if package.startswith("doc."):
        if "plan" in lower or "living-specification" in lower:
            return False
        if file_name in ("README.md", "BILINGUAL.md"):
            return False
    return True
