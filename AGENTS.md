# fastbpmn — agent guide

## Project

Python framework for writing external task workers for BPMN process engines (Camunda 7 / Operaton / Cibseven).
Source at `src/fastbpmn` (library) and `src/squirrel` (CLI runner). Both share a namespace package.

## Setup

- **Package manager:** `uv` (not pip/poetry). Lockfile: `uv.lock`.
- **Install:** `uv sync`
- **Python:** `>=3.11`
- **Build system:** `uv_build` (not setuptools/hatch). Config in `pyproject.toml`.

## Commands (via tox)

| What | Command |
|---|---|
| Test | `tox run -e py311` |
| Lint | `tox run -e ruff` |
| Typecheck | `tox run -e ty` (uses `ty`, **not** mypy/pyright) |

Bare `pytest` from root **ignores** `tests/` (`addopts = "--ignore tests"`). Always run tests via `tox run -e py311` or `pytest tests`.

## Workflow

1. **Plan first** — For non-trivial work, create a task plan in `.opencode/tasks/NNN-descriptive-name.md` (3-digit incrementing number, kebab-case). Outline the approach, files to change, and test strategy before coding.
2. **Write tests** — Every new feature, bug fix, or refactor must include tests. Follow existing test patterns and the quirks below.
3. **Verify quality** — Run `tox run -e py311 && tox run -e ruff && tox run -e ty` before committing. Fix all failures.
4. **Follow existing patterns** — Before implementing, check how similar features are done in the codebase (same imports, same patterns, same conventions).
5. **Keep changes focused** — One logical change per commit. Don't mix refactoring with feature work.
6. **Type-annotate everything** — All new code must have proper type annotations. The `ty` check enforces this.
7. **Update AGENTS.md** — When you discover a new convention or workflow note, add it here for future consistency.

## Pre-commit

Hooks: trailing-whitespace, end-of-file-fixer, check-yaml, gitleaks, uv-lock, sync-with-uv, ruff-check `--fix`, ruff-format.
Run: `pre-commit run --all-files`

## Lint / Format

Config in `pyproject.toml` under `[tool.ruff]`. `ruff.toml` is empty.
Target: `py311`, isort `force-single-line = true`.

## Test quirks

- `pytest-asyncio` with `asyncio_mode = auto` — async test functions need no decorator.
- `asyncio_default_fixture_loop_scope = "module"` — fixture scope for async fixtures.
- Uses `pyfakefs` (filesystem faking), `pytest-httpx` (HTTP mocking), `assertpy` (fluent assertions).
- Coverage via `pytest-cov`, report: `--cov=src --cov-report=term-missing`.

## Docker

Multi-stage build at `docker-images/Dockerfile`.
Install: `uv sync --no-dev --no-editable` (no editable deps, no dev groups).
Requires `libmagic1` (`brew install libmagic` on macOS for local dev).

## CLI entrypoints

- `squirrel` — Typer CLI with `camunda7` subcommand. Entry: `squirrel.app:app`
- `readiness` — legacy health check. Entry: `fastbpmn.readiness:main`
- Programmatic: `squirrel.run(app)` or `Camunda7Server`.

## Docs

Built with [zensical](https://zensical.org). Serve: `uv run --directory docs zensical serve`

## Changelog

Generated via `git-cliff` (conventional commits). Config: `cliff.toml`.

## Notable

- `ruff.toml` is empty — all config lives in `pyproject.toml`.
- `http_tests/` is gitignored — local JetBrains HTTP Client test files.
- Dependency injection system modeled after FastAPI (`Depends()`, `build_dependant()`).
- Routing uses predicate-based matchers (topic, process definition key, tenant) with scoring.
- Middleware stack: `ServerErrorMiddleware` → user middleware → `ExceptionMiddleware` → `ContextMiddleware` → `Camunda7VariablePreprocessor`.
