# -*- coding: utf-8 -*-
"""T030 / R178 / R179 — ToolProcessEnvironment and tool host ensure."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "codimension"))


def test_build_tool_process_environment_inherits_and_overrides():
    from cdmplugins.process_env import build_tool_process_environment

    class FakeEnv:
        def __init__(self):
            self.values = {"PATH": "/usr/bin", "HOME": "/home/u", "VIRTUAL_ENV": "/venv"}

        def insert(self, key, value):
            self.values[key] = value

        def remove(self, key):
            self.values.pop(key, None)

        def value(self, key, default=""):
            return self.values.get(key, default)

    env = build_tool_process_environment(
        "utf-8",
        overrides={"FOO": "bar"},
        env_factory=FakeEnv,
    )
    assert env.value("PATH") == "/usr/bin"
    assert env.value("HOME") == "/home/u"
    assert env.value("VIRTUAL_ENV") == "/venv"
    assert env.value("PYTHONIOENCODING") == "utf-8"
    assert env.value("FOO") == "bar"


def test_module_from_python_args():
    from cdmplugins.process_env import module_from_python_args

    assert module_from_python_args(["-m", "mypy", "x.py"]) == "mypy"
    assert module_from_python_args(["-m", "ruff", "check"]) == "ruff"
    assert module_from_python_args(["check"]) is None
    assert module_from_python_args(None) is None


def test_python_module_available_stdlib():
    from cdmplugins.process_env import python_module_available

    assert python_module_available(sys.executable, "json") is True
    assert python_module_available(sys.executable, "definitely_missing_mod_xyz") is False


def test_python_module_available_ignores_ide_pythonpath(tmp_path, monkeypatch):
    """Probe must not see IDE site-packages via inherited PYTHONPATH."""
    from cdmplugins.process_env import python_module_available

    # Create a fake "foreign" package visible only via PYTHONPATH.
    site = tmp_path / "foreign-site"
    pkg = site / "probe_only_mod_xyz"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("# probe bait\n", encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(site))

    # Inherited env would find it; clean probe must not.
    assert python_module_available(sys.executable, "probe_only_mod_xyz") is False
    # Explicit polluted env still allows opt-in (tests / special hosts).
    polluted = {**os.environ, "PYTHONPATH": str(site)}
    assert python_module_available(sys.executable, "probe_only_mod_xyz", env=polluted) is True


def test_resolve_tool_stays_on_project_when_module_missing(tmp_path, monkeypatch):
    """R179: no silent IDE fallback from resolve()."""
    from unittest.mock import MagicMock

    from utils.analysis_environment import AnalysisEnvironment

    from cdmplugins import process_env as pe

    project_py = str(tmp_path / "proj" / "bin" / "python")
    ide_py = str(tmp_path / "ide" / "bin" / "python")
    site = str(tmp_path / "proj" / "lib" / "site-packages")

    def fake_available(python_path, module, **_kwargs):
        if module != "mypy":
            return False
        return python_path == ide_py

    monkeypatch.setattr(pe, "python_module_available", fake_available)
    monkeypatch.setattr(pe.sys, "executable", ide_py)

    analysis = AnalysisEnvironment(
        python_path=project_py,
        source_kind="configured",
        site_packages_roots=(site,),
        project_id="uuid",
    )
    monkeypatch.setattr(
        "utils.venvbootstrap.buildAnalysisEnvironment",
        lambda _project, for_tools=False: analysis,
    )

    class FakeEnv:
        def __init__(self):
            self.values = {}

        def insert(self, key, value):
            self.values[key] = value

        def remove(self, key):
            self.values.pop(key, None)

        def value(self, key, default=""):
            return self.values.get(key, default)

    proj = MagicMock()
    python_path, env = pe.resolve_tool_python_and_environment(
        proj,
        module="mypy",
        env_factory=FakeEnv,
    )
    assert python_path == project_py
    assert site in env.value("PYTHONPATH", "")


def test_resolve_tool_use_ide_host_explicit(tmp_path, monkeypatch):
    """R179: IDE host only when use_ide_host=True."""
    from unittest.mock import MagicMock

    from utils.analysis_environment import AnalysisEnvironment

    from cdmplugins import process_env as pe

    project_py = str(tmp_path / "proj" / "bin" / "python")
    ide_py = str(tmp_path / "ide" / "bin" / "python")
    site = str(tmp_path / "proj" / "lib" / "site-packages")

    monkeypatch.setattr(pe.sys, "executable", ide_py)

    analysis = AnalysisEnvironment(
        python_path=project_py,
        source_kind="configured",
        site_packages_roots=(site,),
        project_id="uuid",
    )
    monkeypatch.setattr(
        "utils.venvbootstrap.buildAnalysisEnvironment",
        lambda _project, for_tools=False: analysis,
    )

    class FakeEnv:
        def __init__(self):
            self.values = {}

        def insert(self, key, value):
            self.values[key] = value

        def remove(self, key):
            self.values.pop(key, None)

        def value(self, key, default=""):
            return self.values.get(key, default)

    python_path, env = pe.resolve_tool_python_and_environment(
        MagicMock(),
        module="mypy",
        env_factory=FakeEnv,
        use_ide_host=True,
    )
    assert python_path == ide_py
    assert site in env.value("PYTHONPATH", "")


def test_pip_package_for_module():
    from cdmplugins.tool_host import pip_package_for_module

    assert pip_package_for_module("mypy") == "mypy"
    assert pip_package_for_module("pip_audit") == "pip-audit"
    assert pip_package_for_module("custom_tool") == "custom-tool"


def test_ensure_install_into_project(tmp_path, monkeypatch):
    """R179: Install choice runs pip into project Python and re-probes."""
    from unittest.mock import MagicMock

    from utils.analysis_environment import AnalysisEnvironment

    from cdmplugins import process_env as pe
    from cdmplugins import tool_host as th

    project_py = str(tmp_path / "proj" / "bin" / "python")
    site = str(tmp_path / "proj" / "lib" / "site-packages")
    installed = {"mypy": False}

    def fake_available(python_path, module, **_kwargs):
        if module != "mypy":
            return False
        if python_path != project_py:
            return False
        return installed["mypy"]

    monkeypatch.setattr(pe, "python_module_available", fake_available)
    monkeypatch.setattr(th, "python_module_available", fake_available)

    analysis = AnalysisEnvironment(
        python_path=project_py,
        source_kind="configured",
        site_packages_roots=(site,),
        project_id="uuid",
    )
    monkeypatch.setattr(
        "utils.venvbootstrap.buildAnalysisEnvironment",
        lambda _project, for_tools=False: analysis,
    )
    monkeypatch.setattr(
        "utils.venvbootstrap.requireMutableProjectPython",
        lambda _project: project_py,
    )

    calls: list[list[str]] = []

    def fake_install(cmd, cwd, project_dir):
        calls.append(cmd)
        installed["mypy"] = True

    class FakeEnv:
        def __init__(self):
            self.values = {}

        def insert(self, key, value):
            self.values[key] = value

        def remove(self, key):
            self.values.pop(key, None)

        def value(self, key, default=""):
            return self.values.get(key, default)

    proj = MagicMock()
    proj.getProjectDir.return_value = str(tmp_path)

    result = th.ensure_tool_python_and_environment(
        proj,
        module="mypy",
        env_factory=FakeEnv,
        choice_provider=lambda **_kwargs: "install",
        install_runner=fake_install,
    )
    assert not isinstance(result, str)
    python_path, env = result
    assert python_path == project_py
    assert calls and "mypy" in calls[0]
    assert site in env.value("PYTHONPATH", "")


def test_ensure_ide_once(tmp_path, monkeypatch):
    """R179: Use IDE tools once keeps project site-packages."""
    from unittest.mock import MagicMock

    from utils.analysis_environment import AnalysisEnvironment

    from cdmplugins import process_env as pe
    from cdmplugins import tool_host as th

    project_py = str(tmp_path / "proj" / "bin" / "python")
    ide_py = str(tmp_path / "ide" / "bin" / "python")
    site = str(tmp_path / "proj" / "lib" / "site-packages")

    def fake_available(python_path, module, **_kwargs):
        return module == "mypy" and python_path == ide_py

    monkeypatch.setattr(pe, "python_module_available", fake_available)
    monkeypatch.setattr(th, "python_module_available", fake_available)
    monkeypatch.setattr(pe.sys, "executable", ide_py)
    monkeypatch.setattr(th.sys, "executable", ide_py)

    analysis = AnalysisEnvironment(
        python_path=project_py,
        source_kind="configured",
        site_packages_roots=(site,),
        project_id="uuid",
    )
    monkeypatch.setattr(
        "utils.venvbootstrap.buildAnalysisEnvironment",
        lambda _project, for_tools=False: analysis,
    )
    monkeypatch.setattr(
        "utils.venvbootstrap.requireMutableProjectPython",
        lambda _project: project_py,
    )

    class FakeEnv:
        def __init__(self):
            self.values = {}

        def insert(self, key, value):
            self.values[key] = value

        def remove(self, key):
            self.values.pop(key, None)

        def value(self, key, default=""):
            return self.values.get(key, default)

    result = th.ensure_tool_python_and_environment(
        MagicMock(),
        module="mypy",
        env_factory=FakeEnv,
        choice_provider=lambda **_kwargs: "ide",
    )
    assert not isinstance(result, str)
    python_path, env = result
    assert python_path == ide_py
    assert site in env.value("PYTHONPATH", "")


def test_ensure_offers_install_for_project_venv_without_tool(tmp_path, monkeypatch):
    """Project venv without mypy → ensure prompts (not silent start)."""
    from unittest.mock import MagicMock

    from utils.analysis_environment import AnalysisEnvironment

    from cdmplugins import process_env as pe
    from cdmplugins import tool_host as th

    # Synthetic project venv python (no host-specific absolute paths).
    project_py = str(tmp_path / "proj" / "bin" / "python")
    os.makedirs(os.path.dirname(project_py), exist_ok=True)
    with open(project_py, "w", encoding="utf-8") as handle:
        handle.write("#!/bin/sh\nexit 1\n")
    os.chmod(project_py, 0o755)

    # Pollute like a mis-launched IDE: PYTHONPATH includes Codimension tools.
    ide_site = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".venv",
        "lib",
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        "site-packages",
    )
    if os.path.isdir(ide_site):
        monkeypatch.setenv("PYTHONPATH", ide_site)

    monkeypatch.setattr(pe, "python_module_available", lambda *_a, **_k: False)
    monkeypatch.setattr(th, "python_module_available", lambda *_a, **_k: False)

    analysis = AnalysisEnvironment(
        python_path=project_py,
        source_kind="configured",
        site_packages_roots=(),
        project_id="project-venv-missing-tool",
    )
    monkeypatch.setattr(
        "utils.venvbootstrap.buildAnalysisEnvironment",
        lambda _project, for_tools=False: analysis,
    )
    monkeypatch.setattr(
        "utils.venvbootstrap.requireMutableProjectPython",
        lambda _project: project_py,
    )

    class FakeEnv:
        def __init__(self):
            self.values = {}

        def insert(self, key, value):
            self.values[key] = value

        def remove(self, key):
            self.values.pop(key, None)

        def value(self, key, default=""):
            return self.values.get(key, default)

    choices: list[str] = []

    def provider(**kwargs):
        choices.append(kwargs["module"])
        return "cancel"

    result = th.ensure_tool_python_and_environment(
        MagicMock(),
        module="mypy",
        env_factory=FakeEnv,
        choice_provider=provider,
    )
    assert isinstance(result, str)
    assert "mypy" in result
    assert choices == ["mypy"]


def test_ensure_cancel_headless(tmp_path, monkeypatch):
    """R179: without UI / choice_provider → soft error, no install."""
    from unittest.mock import MagicMock

    from utils.analysis_environment import AnalysisEnvironment

    from cdmplugins import process_env as pe
    from cdmplugins import tool_host as th

    project_py = str(tmp_path / "proj" / "bin" / "python")

    monkeypatch.setattr(pe, "python_module_available", lambda *_a, **_k: False)
    monkeypatch.setattr(th, "python_module_available", lambda *_a, **_k: False)

    analysis = AnalysisEnvironment(
        python_path=project_py,
        source_kind="configured",
        site_packages_roots=(),
        project_id="uuid",
    )
    monkeypatch.setattr(
        "utils.venvbootstrap.buildAnalysisEnvironment",
        lambda _project, for_tools=False: analysis,
    )
    monkeypatch.setattr(
        "utils.venvbootstrap.requireMutableProjectPython",
        lambda _project: project_py,
    )

    class FakeEnv:
        def __init__(self):
            self.values = {}

        def insert(self, key, value):
            self.values[key] = value

        def remove(self, key):
            self.values.pop(key, None)

        def value(self, key, default=""):
            return self.values.get(key, default)

    result = th.ensure_tool_python_and_environment(
        MagicMock(),
        module="mypy",
        env_factory=FakeEnv,
    )
    assert isinstance(result, str)
    assert "not installed" in result
    assert "mypy" in result


def test_build_tool_environ_applies_analysis_env(tmp_path):
    """R112 headless environ mirrors process_env analysis_env handling."""
    sys.modules.pop("utils.analysis_environment", None)

    from utils.analysis_environment import AnalysisEnvironment

    from codimension.infrastructure.process import build_tool_environ

    venv = tmp_path / ".venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
    site = venv / "lib" / "python3.12" / "site-packages"
    site.mkdir(parents=True)
    analysis = AnalysisEnvironment.from_source(
        "auto",
        str(venv / "bin" / "python"),
        site_packages_roots=[str(site)],
        resolve_site_packages=False,
    )
    env = build_tool_environ(
        "utf-8",
        analysis_env=analysis,
        base={"PATH": "/bin", "PYTHONPATH": "/old"},
    )
    assert env["VIRTUAL_ENV"] == str(venv)
    assert env["PYTHONPATH"].startswith(str(site))
    assert "/old" in env["PYTHONPATH"]
    assert env["PYTHONIOENCODING"] == "utf-8"
