# rv — CLI PR code review tool

Python 3.12+, managed with `uv`. Entrypoint: `rv.cli.main:app` (Typer).

## Commands

```sh
uv sync                        # install deps
make format                    # ruff format + ruff check --fix --unsafe-fixes
make typecheck                 # uv run ty check .  (NOT mypy/pyright)
make test                      # uv run pytest
```

## Architecture: hexagonal (ports-and-adapters)

```
src/rv/
  domain/       — pure logic, zero external imports (Protocol ports in ports.py)
  adapters/     — external integrations (Git, GitHub/GraphQL, Peewee/SQLite, subprocess)
  cli/          — Typer entrypoint + Rich UI
```

Actions in `domain/actions/` receive port implementations + a `ui` Protocol — never depend on adapters or CLI directly.

DI: manual `CLIDeps` class with `@cached_property` in `cli/_deps.py`.

## Testing

- `asyncio_mode = auto` in pyproject.toml — async tests work without decorators.
- `filterwarnings = ["error"]`.
- Domain action tests: mock ports with `create_autospec`.
- Store tests: in-memory SQLite (`SqliteDatabase(":memory:")`).
- GitHub adapter tests: `pytest-recording` (VCR) — cassettes in `tests/fixtures/*.yaml`, `Authorization` header filtered out, token expiration mangled.
- Git/runner tests: real subprocess in tmpdirs.
- Integration tests (`tests/adapters/test_github.py`): require `GITHUB_TOKEN` PAT (scoped `repo`), access to `alexjuda/rv-testing` private repo, and `gh` CLI.
- Re-record cassettes: `rm -r tests/fixtures && GITHUB_TOKEN=ghp_... uv run pytest tests/ --record-mode=once` (run `scripts/check-test-fixtures.sh` first).

## Conventions

- Python 3.12+ typing (list[X], dict[K,V], `|` for unions).
- `ruff.toml`: extremely comprehensive rule set (~350+ rules). Code must pass both format + check.
- `ty` for type checking (not mypy). Keep type-ignored code as minimal as possible. If there's no way to make typing work, extract the type-ignored code to small, quarantined modules.
- Dataclasses for all domain models. Frozen-style (`@dataclass` with no setters).
- Relative imports when inside `src`, absolute imports when inside `tests`.
