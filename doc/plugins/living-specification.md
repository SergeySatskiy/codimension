# Living Specification: Плагіни Codimension

> **Мова / Language:** Українська | [English](../en/plugins/living-specification.md)

<!-- markdownlint-disable MD060 -->

**Версія:** 1.4  
**Дата:** 2026-08-08  
**Джерело:** [plugins-implementation-plan.md](plugins-implementation-plan.md)

Матриця відповідності «ТЗ → модуль → тести». Оновлюється при кожній зміні плагінів.

---

## 1. Матриця ТЗ → модуль → тести

| ТЗ (план) | Модуль | Файли | Тести |
| --------- | ------ | ----- | ----- |
| **Фаза 1: Coverage** | cdmplugins.coverage | coverage.cdmp, __init__.py, coveragedriver.py, coverageresultviewer.py | Smoke: Run with coverage (Ctrl+Shift+C), вкладка результатів |
| **Фаза 2: Bandit** | cdmplugins.bandit | bandit.cdmp, __init__.py, banditdriver.py (LintDriverBase), banditresultviewer.py | Smoke: Run bandit (Ctrl+Shift+B); unit: tests/test_lint_drivers.py |
| **Фаза 3: pip-audit** | cdmplugins.pipaudit | pipaudit.cdmp, __init__.py, pipauditdriver.py, pipauditresultviewer.py | Smoke: Audit dependencies (Ctrl+Shift+A), вкладка CVE |
| **Фаза 4: Ruff format** | cdmplugins.ruffformat | ruffformat.cdmp, __init__.py, ruffformatdriver.py, ruffformatconfig.py | Smoke: Format (Ctrl+Shift+F), format-on-save (config) |
| **Фаза 5: TODO panel** | cdmplugins.todopanel | todopanel.cdmp, __init__.py, todopaneldriver.py, todopanelviewer.py, todoscanner.py | Smoke: Scan TODO (Ctrl+Shift+O), unit: tests/test_todoscanner.py |
| **Референс: Ruff** | cdmplugins.ruff | ruff.cdmp, __init__.py, ruffdriver.py (LintDriverBase), ruffresultviewer.py | Smoke: Run ruff (Ctrl+Shift+R); unit: tests/test_lint_drivers.py |
| **Референс: Mypy** | cdmplugins.mypy | mypy.cdmp, mypydriver.py (JSONL) | Smoke: Ctrl+Shift+M; unit: tests/test_lint_drivers.py |
| **Референс: Pytest** | cdmplugins.pytest | pytest.cdmp, __init__.py, pytestdriver.py, pytestresultviewer.py | Smoke: Run pytest (Ctrl+Shift+T) |
| **Базовий клас** | cdmplugins.lintdriverbase | lintdriverbase.py, process_env.py | systemEnvironment + non-blocking stop |
| **Git VCS / PAT** | cdmplugins.git | gitconfig.py, credentials.py, githubapi.py | gh→keyring→0600; tests/test_credentials_and_atomic.py |
| **Atomic `.cdm3`** | utils.atomic_io / project_schema | atomic_io.py, project_schema.py, project.py | atomic save; schema on load/update/reload; tests/test_project_persistence.py |
| **Project scan T050–T052** | utils.project_scan / project / watcher | project_scan.py, project.py, watcher.py | path-aware exclude; symlink visited; async scan; tests/test_project_scan.py |
| Packaging / CI T060–T067 | pyproject / CI | pyproject.toml, requirements.txt, requirements-runtime.txt, constraints.txt, ci.yml, release.yml, scripts/offscreen_gui_smoke.py | deps groups; matrix 3.10–3.13; constraints gate; wheel; offscreen smoke; release verify |
| **Shim identity T071–T073** | parsers / bootstrap | parsers/__init__.py, check_package_relative_imports.py | unified cdmpyparser/cdmcfparser aliases; T072 CI gate |
| **Headless core T080–T082** | core / infrastructure | core/syntax.py, core/flow.py, infrastructure/* | tests/test_core_headless.py |
| **ApplicationServices R101** | app | app/__init__.py, app/services.py | headless façade + fakes; tests/test_app_services.py; T085 covers `codimension/app` |
| **App routing R102** | ui + globals + startup | globals.py `appServices`; mainwindow / projectviewer / recentprojectsviewer / codimension.py | UI→app→project; tests/test_r102_app_routing.py |
| **Module boundaries R103** | CI | scripts/check_module_boundaries.py | named-layer matrix core/infra/app/utils/ui/plugins; tests/test_module_boundaries.py |
| **Core import graph T085 / R100** | CI + utils | scripts/check_core_import_graph.py; utils/importutils.py | no Qt/UI in core/infrastructure/app; `importutils` Qt-free + progress callback; tests/test_importutils.py, test_t085_core_import_graph.py |
| **MainWindow routing T083** | ui.mainwindow / mainwindow_debug | mainwindow.py, mainwindow_debug.py | MRO mixins; no extendInstance; DebuggerMixin |
| **Lazy GlobalData T084** | utils.globals | globals.py | create-on-first-call; tests/test_globals_lazy.py |
| **Debugger session e2e T100–T102** | debugger + utils.run / runmanager | run.py (`_debuggerClientPath`); tests/debugger/ | session-first offscreen: stop-at-first-line, continue, step/stop |
| **Debugger CI T103** | CI | `.github/workflows/ci.yml` | `QT_QPA_PLATFORM=offscreen pytest tests/debugger/ -m debugger_session` |
| **Debugger mixin routing T110–T111** | ui.mainwindow_debug + tests/debugger | host.py `create_mixin_host`; test_mixin_routing.py | switchDebugMode chrome + `_onDbgGo`→remoteContinue |
| **Debugger widget smoke T120** | debugger.bpwp / excpt | test_widgets_bpwp.py, test_widgets_exceptions.py; pytest-qt | offscreen panel add/clear/ignore; Skin bootstrap fixture |
| **Debugger full-IDE T130** | ui.mainwindow + utils.skin | `ide_bootstrap.py`, `test_full_ide_smoke.py`; `PACKAGE_SKIN_DIR` package-relative; `.github/workflows/debugger-full-ide-nightly.yml` | env `CDM_FULL_IDE_SMOKE=1`; nightly (не PR-blocker); моніторити workflow |
| **Project venv bootstrap T140** | utils.venvbootstrap + ui.venvsetupdlg / venvprocess | venvbootstrap.py, venvsetupdlg.py, venvprocess.py; tests/test_venv_bootstrap.py, test_venv_process.py | explicit VENV/Update; async QProcess create/pip (A03); session overlay |
| **Analysis env refresh T141** | utils.venvbootstrap + project + status bar | `describeAnalysisPythonSource`, `requestAnalysisEnvironmentRefresh`, `Project.refreshAnalysisEnvironment`, `sbAnalysisEnv`; tests/test_venv_bootstrap.py | re-analyze after VENV/Update; Env: project/session/auto/IDE; unresolved opt-in multi-select |
| **AnalysisEnvironment R110** | utils.analysis_environment | analysis_environment.py | frozen dataclass (path/kind/site-packages/project_id); parity with describe kinds; tests/test_analysis_environment.py |
| **buildAnalysisEnvironment R111** | utils.venvbootstrap | `buildAnalysisEnvironment`; `getEffectiveProjectPython` / status via env | single constructor; precedence tests in test_analysis_environment.py |
| **Drivers ↔ AnalysisEnvironment R112** | cdmplugins.process_env + drivers | `resolve_tool_python_and_environment`; LintDriverBase / coverage / pytest / pipaudit / ruffformat | PYTHONPATH/VIRTUAL_ENV from env; tests/test_lint_drivers.py, test_process_env.py |
| **Analysis cache registry R113** | utils.analysis_cache + brief/flow caches | `invalidate(project\|file\|env)`; ControlFlowInfoCache; wire env refresh / FS / save | tests/test_analysis_cache.py |
| **Auto-attach project venv R114** | utils.venvbootstrap + Settings + Options | `maybeAutoAttachProjectVenv`; superseded by R176 policy | tests/test_venv_bootstrap.py |
| **Project venv policy R176** | utils.venvbootstrap + Settings + Options + status bar | `projectVenvPolicy` (`manual`/`auto_session`/`auto_persist`); `applyProjectVenvPolicyOnOpen`; diagnostics WARNINGs; Env: double-click | tests/test_venv_bootstrap.py |
| **Log click-to-source R177** | utils.log_location + ui.logviewer + importutils | `parse_log_location`; import errors `path:line:`; Log click → `openFile`; frozen stdlib resolved | tests/test_log_location.py, test_importutils.py |
| **Tool host fallback R178** | cdmplugins.process_env | `python_module_available`; explicit `use_ide_host` (no silent fallback) | tests/test_process_env.py |
| **Install missing tool R179** | cdmplugins.tool_host + drivers | Dialog Install / IDE once / Cancel; pip into mutable project venv | tests/test_process_env.py |
| **Tool probe env isolation** | cdmplugins.process_env | Clean-env ``python_module_available``; strip IDE PYTHONPATH for tool QProcess | tests/test_process_env.py |
| **Product docs isolation** | utils.embedded_docs + package_docs_filter + doc/user | Help fail-closed → `doc/user/index.md`; shared wheel filter; no repo-root `.cdm3` | tests/test_embedded_docs.py |
| **Recent files prune** | utils.fsenv + recent viewer + IDE smoke | Drop missing/`pytest-of-*`/`t130-script`; smoke uses temp Settings dir | tests/test_fsenv.py |
| **DependencyManifest R120** | utils.dependency_manifest | `buildDependencyManifest`; lock_hint; export script; collectInstallSources delegate | tests/test_dependency_manifest.py |
| **ExecutionTarget R121** | core.execution | Protocol `run`/`debug`/`profile`/`which_python`; ExecutionRequest/Result | tests/test_execution_target.py |
| **LocalExecutionTarget R122** | utils.local_execution + utils.run | `LocalExecutionTarget`; `getCwdCmdEnv` via protocol | tests/test_local_execution.py, test_run_argv.py |
| **DockerExecutionTarget R123** | utils.docker_execution | image + workspace mount + `docker run` argv; docker-or-skip | tests/test_docker_execution.py |
| **SSHExecutionTarget R124** | utils.ssh_execution | `SSHTransport` + Fake/Subprocess; remote-path sync MVP | tests/test_ssh_execution.py; [ssh-execution.md](../technology/ssh-execution.md) |
| **KubernetesExecutionTarget R125** | utils.k8s_execution | `K8sJobTransport` + Fake/kubectl; Job stub metadata | tests/test_k8s_execution.py; [k8s-execution.md](../technology/k8s-execution.md) |
| **SymbolIndex schema R130** | core.symbol_index | SymbolRecord/Kind/SourceSpan/SymbolIndex | tests/test_symbol_index.py |
| **SymbolIndex ← brief_ast R131** | utils.symbol_index_brief | `index_source` / `build_symbol_index` + on_file | tests/test_symbol_index_brief.py |
| **SymbolIndex queries R132** | core.symbol_index + search.occurrencesprovider | `find_definitions` / `find_references`; index→occurrences bridge | tests/test_symbol_index_queries.py, test_occurrencesprovider.py |
| **DependencyGraph R133** | utils.dependency_graph | `build_dependency_graph` / from_sources; JSON/DOT; local vs external | tests/test_dependency_graph.py |
| **MetricProvider R134** | core.metrics + utils.radon_cc_provider | Protocol + registry; radon CC adapter | tests/test_metric_provider.py |
| **OverlayLayer R135** | core.overlay + utils.overlay_host | Protocol + registry; flow redraw / editor update attach | tests/test_overlay.py |
| **Advanced metrics R136** | utils.radon_metrics_pack | MI + Halstead volume + raw LOC as MetricProvider | tests/test_radon_metrics_pack.py |
| **Git analytics R137** | utils.git_analytics | churn/hotspot from `git log --numstat`; text formatter | tests/test_git_analytics.py |
| **Risk score R138** | core.risk_score | `compute_risk_score` lint+metrics±git (`cdm-risk-v1`) | tests/test_risk_score.py |
| **Branching policy R170** | docs | CONTRIBUTING(+.en): `master` + `feature/*`/`fix/*`; no direct push; `ci-gate` | GitHub branch protection + docs gate |
| **CFG graph model R140.a** | core.cfg | `CfgNode`/`CfgEdge`/`CfgGraph`; `build_cfg_graph` from flow parse | tests/test_cfg_graph.py |
| **CFG canvas bind R140.b** | flowui.cfg_adapter + vcanvas/flowuiwidget | `bind_cfg_graph` у `layoutModule`; `getCfgGraph`; CF-дерево = layout payload | tests/test_cfg_adapter.py |
| **CFG frame map R141** | core.cfg_frames + debugger.stackviewer | `map_frame_to_cfg_node` / stack; tooltip CFG id; manual: stop у debugger → tip показує node | tests/test_cfg_frames.py |
| **CFG graph diff R142** | core.cfg_diff | `diff_cfg_graphs` / `diff_cfg_sources`; стабільні content keys; add/remove/change | tests/test_cfg_diff.py |
| **Taint MVP R143** | core.taint | Function-local sources→sinks; задокументована підмножина | tests/test_taint.py; [taint-mvp.md](../uk/technology/taint-mvp.md) |
| **Plugin capabilities R150** | plugins.capabilities + pluginmanager | `PluginCapabilitySpec` / negotiate; host відхиляє несумісні | tests/test_plugin_capabilities.py |
| **AI context R151** | core.ai_context | Pack SymbolIndex + CFG slice для символу; JSON; без мережі | tests/test_ai_context.py |
| **AI UI R152** | core.ai_ui + editor.editorcontextmenus + ui.aisettingsdlg + Options | Options top-level Enable AI / AI settings…; ПКМ AI; `ai_ui` / `CDM_AI_UI`; offline | tests/test_ai_ui.py, test_ai_options_menu.py |
| **Feature flags R174** | core.feature_flags | Persistent JSON flags; env overrides; гейт AI UI | tests/test_feature_flags.py |
| **Safe mode R175** | core.safe_mode + codimension/pluginmanager/overlays | `--safe-mode` / `CDM_SAFE_MODE`; без плагінів і overlays | tests/test_safe_mode.py |
| **Env overlay R160** | utils.environment_overlay + editor.flowuinavbar | Бейджі `env:source` + path на flow nav через R135; status bar → `env` | tests/test_environment_overlay.py |
| **Deps overlay R161** | utils.dependency_overlay + diagram.depsitems | Edge heat з DependencyGraph; nav badges; tint connector | tests/test_dependency_overlay.py |
| **Deploy overlay R162** | utils.deployment_overlay + editor.flowuinavbar | Read-only Dockerfile/Compose hints; nav badges | tests/test_deployment_overlay.py; fixtures/deployment |
| **Release channel R171** | cdmverspec | `release_channel` + `get_release_channel` / env override; одна версія | tests/test_cdmverspec.py |
| **Update check R172** | utils.update_check + ui.mainmenu/mainwindow | GitHub Releases read-only; діалог новішого тега; injectable fetch | tests/test_update_check.py |
| **Update download R173** | utils.update_download + ui.mainwindow | Download у cache; SHA-256 fail closed; без apply | tests/test_update_download.py |
| **Flow AST fallback** | codimension.parsers.flow_ast | flow_ast.py | unit: tests/test_flow_ast.py; conformance: tests/conformance/ (T004–T028.1); comment binder: parsers/comment_binder.py; UI coupling: test_flow_ui_coupling.py |
| **Brief AST fallback** | codimension.parsers.brief_ast | brief_ast.py | unit: tests/test_brief_ast.py; conformance: tests/conformance/ (T006–T018) |
| **Parser contract** | docs | [technology/parser-contract.md](../technology/parser-contract.md), [uk](../uk/technology/parser-contract.md) | Living Spec + conformance gates |
| **Source spans** | codimension.parsers.source_spans | source_spans.py (T003) | unit: tests/test_source_spans.py |
| **Binary hexdump** | codimension.utils.binfiles | binfiles.py | unit: tests/test_binfiles.py |
| **Markdown (mistune 3)** | codimension.utils.md | md.py | unit: tests/test_md.py |
| **FS smart zoom** | codimension.editor.flowuiwidget | flowuiwidget.py | unit: tests/test_flowuiwidget.py |
| **Debugger watchpoints** | codimension.debugger | wputils.py, editwatchpoint.py, server.py, wpointviewer.py | unit: tests/test_watchpoints.py |
| **Greenlet debugger** | codimension.debugger.client | threadextension_cdm_dbg.py, threadutils_cdm_dbg.py | unit: tests/test_greenlet_trace.py |
| **Occurrences search redo** | codimension.search | occurrencesprovider.py, searchresultsviewer.py | unit: tests/test_occurrencesprovider.py |

---

## 2. CI-перевірки

| Перевірка | Команда | Джерело |
| --------- | ------- | ------- |
| T072 import gate | `python scripts/check_package_relative_imports.py` | .github/workflows/ci.yml |
| T085/R100 import graph | `python scripts/check_core_import_graph.py` | .github/workflows/ci.yml |
| R103 module boundaries | `python scripts/check_module_boundaries.py` | .github/workflows/ci.yml |
| Ruff lint | `ruff check codimension cdmplugins` | .github/workflows/ci.yml |
| Ruff format | `ruff format --check codimension cdmplugins` | .github/workflows/ci.yml |
| Mypy | `mypy $(find codimension cdmplugins -name '*.py' ! -path '*/flowui/everything.py')` | .github/workflows/ci.yml |
| Smoke | `import codimension; import cdmplugins` | .github/workflows/ci.yml |
| Offscreen GUI | `QT_QPA_PLATFORM=offscreen python scripts/offscreen_gui_smoke.py` | .github/workflows/ci.yml |
| Wheel | `python -m build` + clean venv `pip install` + `pip check` | .github/workflows/ci.yml |
| pip-audit | `pip-audit -r requirements.txt` | .github/workflows/ci.yml |
| Pytest | `pytest tests/` (matrix 3.10–3.13; count from latest green Actions run) | .github/workflows/ci.yml |
| Docs links | `python scripts/check_docs.py` (links/images/dirs/anchors/ref/HTML; UA↔EN; TODO↔Living Spec; CI matrix) | .github/workflows/ci.yml |

---

## 3. Відповідність плану

- [x] Усі плагіни в `cdmplugins/`
- [x] setup.py оновлено
- [x] requirements.txt оновлено
- [x] Документація оновлена (plugins.md, living-specification.md)
- [x] CI: перевіряти останній green Actions run на `master` (не зберігати static SHA/test count у цьому файлі)
- [x] Документація: [doc/README.md](../README.md)

### Відкриті пункти аудиту (після PR #37 / 44cc1794)

| ID | Тема | Статус |
|----|------|--------|
| B01–B02 / C01 / D01 / E01 / E02 | VENV guards, base interpreter, custom-terminal argv/profile | ✅ |
| E04 / F07 | launcher unlink + symlink-safe stale cleanup (one-shot legacy `/tmp`) | ✅ |
| E05 | profile marker + start-based timeout + `.done` cleanup | ✅ |
| E06 | exec probe + DQ-safe paths (spaces/Unicode; shebang no whitespace) | ✅ |
| D02 / B07 | transactional VENV create/recreate (staging + commit) | ✅ |
| C02 / C03 | interpreter probe + recreate base (no silent IDE version swap) | ✅ |
| B04 / D05 | brief header/target positions + encoding cookie line-2 | ✅ |
| B05 / B06 / D04 / D06 | CML clustering, case token, multiline side comments | ✅ |
| D07 / B08 / C04 | production startup + plugin load; Flow UI import gate | ✅ |
| B03 | cooperative scan cancel + coalescing + no GUI sync fallback | ✅ |
| B11 | Docs drift / docs gate coverage / `doc/uk` parity | ✅ |
| B09 / B10 / C05 | schema on all update paths; atomic settings flush; uuid4 + immediate persist | ✅ |
| D08 / E03 / G01 | constraints snapshot; release verify + OIDC publish; `ci-gate` + master protection | ✅ |

Подальша черга: [ROADMAP.uk.md](../../ROADMAP.uk.md) — **активна черга порожня**; deferred R180–R182 лише за явним запитом.

### Матриця меж модулів (R103)

Імпортер → дозволені **іменовані** шари (інші пакети поза матрицею). Qt заборонено в `core` / `infrastructure` / `app`.

| Імпортер | Дозволено імпортувати |
| -------- | --------------------- |
| core | *(жоден іменований шар)* |
| infrastructure | core, utils |
| app | core, infrastructure, utils |
| utils | core, infrastructure, app, ui*, plugins* |
| ui | core, infrastructure, app, utils, plugins |
| plugins | core, infrastructure, app, utils, ui |

\*legacy: `utils → ui|plugins` дозволено тимчасово (GlobalData / Qt-хелпери); ціль — прибрати в наступних задачах.

Gate: `python scripts/check_module_boundaries.py`

---

## 4. Оновлення

При додаванні/зміні плагіна:

1. Додати рядок у матрицю (розд. 1).
2. Оновити setup.py (getPackages, package_data).
3. Оновити requirements.txt (якщо нова залежність).
4. Додати посилання на цей документ у MR.
