# Project Instructions

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Language | Python 3.10+ | Union syntax `X \| Y`, match statements OK |
| HTTP client | httpx | Only runtime dependency |
| Build | uv + uv_build | `uv sync --all-extras` to install everything |
| Linter/formatter | ruff | line-length=120, double quotes, space indent |
| Type checker | ty (Astral) | `uv run ty check cortex_agents/` |
| Tests | pytest + coverage | 80% threshold enforced |
| Docs | mkdocs-material | `make serve-docs` |

## Code Style

- Line length: **120 characters** (ruff)
- Quotes: **double quotes** in code and docstrings
- Imports: isort-style (ruff `I` rules); stdlib → third-party → local
- Type annotations: always on public APIs; use `X | Y` union syntax (not `Optional[X]`)
- Internal/private helpers: prefix with `_` (e.g. `_transport.py`, `_retry.py`)

## Testing

```bash
make tests       # pytest (verbose, with coverage)
make coverage    # also produces HTML/XML reports; fails under 80%
```

- Test files: `tests/test_*.py` — mirror source module name (e.g., `test_transport.py`)
- Test classes: `Test*`, test functions: `test_*`
- Fixtures live in `tests/conftest.py`
- Coverage source: `cortex_agents/` only

## Build & Run

```bash
make sync        # uv sync --all-extras (install all deps)
make format      # ruff format + ruff check --fix
make lint        # ruff check (no auto-fix)
make ty          # ty type check
make check       # format + lint + ty + tests (full pre-commit equivalent)
make build-docs  # mkdocs build
make serve-docs  # mkdocs serve (localhost:8000)
```

## Project Structure

```
cortex_agents/         Main package (module root = repo root)
  base.py              BaseAgent ABC — credentials, URL building, logging
  agent.py             CortexAgent (sync)
  async_agent.py       AsyncCortexAgent
  analyst.py           CortexAnalyst (sync)
  async_analyst.py     AsyncCortexAnalyst
  _retry.py            retry_with_backoff decorator (sync + async)
  _streaming.py        SSE stream helpers
  _base_response.py    BaseSSEResponse — shared SSE parser
  core/
    _transport.py      SyncTransport / AsyncTransport (httpx wrappers)
    response.py        AgentResponse — rich SSE event accessor
    entity.py          Agent CRUD (create/get/update/list/delete)
    run.py             AgentRun + AgentInlineConfig
    threads.py         Thread CRUD
    feedback.py        Feedback submission
tests/                 pytest suite (unit + SSE parsing)
examples/              Runnable usage examples
docs/                  MkDocs source
```

## Environment

Copy `.env.example` → `.env` and fill in:

```
SNOWFLAKE_ACCOUNT_URL=https://your-account.snowflakecomputing.com
SNOWFLAKE_PAT=your-personal-access-token
```

Both can also be passed directly to client constructors.

## Conventions

- Commit style: short imperative (e.g., "Harden _transport", "Add retry logic")
- Pre-commit hooks: ruff-check, ruff-format, ty — run `pre-commit install` once
- Error type: always raise/catch `SnowflakeAPIError` at the public boundary (not raw httpx errors)
- Retry targets: 429 and 5xx status codes, plus `httpx.TimeoutException` / `httpx.ConnectError`
- URL path segments are percent-encoded in `BaseAgent._get_url()` — never build raw f-string URLs
- SSE responses are lazy: events accumulate on first iteration; `.text`, `.sql` etc. call `_ensure_parsed()`
