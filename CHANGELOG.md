# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-13

### Added

- **Cortex Agents client** (`CortexAgent` / `AsyncCortexAgent`) — run, create, get, update, list, and delete agents via the Snowflake Cortex REST API
- **Cortex Analyst client** (`CortexAnalyst` / `AsyncCortexAnalyst`) — generate SQL from natural language using semantic model files or semantic views
- **Async-first design** — all clients have a fully async counterpart; use `async with` and `await` throughout
- **SSE streaming** — responses stream Server-Sent Events in real-time; events accumulate lazily and are accessible via `.text`, `.sql`, etc. after iteration
- **`AgentResponse`** — rich accessor object exposing `.text`, `.sql`, `.sql_explanation`, `.query_id`, `.thinking`, `.message_id`, `.run_id`, `get_sql_result()`, `get_token_usage()`, `get_warnings()`, `get_suggested_queries()`, `get_annotations()`, `is_elicitation`, and `.events`
- **Thread management** (`create_thread`, `get_thread`, `list_threads`, `delete_thread`) — server-side conversation context for multi-turn agent sessions
- **`AgentInlineConfig`** — pass agent configuration inline (models, instructions, tools, tool resources) without a pre-created agent object
- **Agent CRUD** — full lifecycle management: create, retrieve, update, list, and delete named agents
- **Feedback submission** — `submit_feedback()` on both `CortexAgent` and `CortexAnalyst`
- **`suggest_questions()`** on `CortexAnalyst` — returns sample questions a semantic model can answer
- **`validate_semantic_model()`** on `CortexAnalyst` — validates a semantic model file or view before querying
- **`list_models()`** on `CortexAgent` — enumerates available LLM models
- **Multi-model selection** — pass a list of semantic models to `CortexAnalyst.message()` and let Analyst pick the best fit
- **Chart utilities** (`plot_charts`, `plot_chart_dict`, `extract_chart_specs`, `get_chart_info`, `chart_to_json`) — render Vega-Lite chart specs from agent responses via Altair; works in Jupyter and Streamlit
- **`BaseSSEResponse`** — shared SSE parsing base class used by both `AgentResponse` and `AnalystResponse`
- **Retry with exponential backoff** (`_retry.py`) — automatic retries on HTTP 429 / 5xx and `httpx.TimeoutException` / `httpx.ConnectError`, with jitter; sync and async decorators
- **`SyncTransport` / `AsyncTransport`** — thin httpx wrappers that own connection lifecycle; guard against simultaneous `stream=True` + `params` to prevent request-body corruption
- **Key-pair JWT authentication** — pass `token_type="KEYPAIR_JWT"` to use a keypair JWT instead of a PAT
- **`load_credentials()`** utility — resolves `account_url` and `pat` from constructor args, environment variables, or a `.env` file (optional `python-dotenv` extra)
- **Optional extras** — `charts` (Altair + Pandas), `dotenv` (python-dotenv), `all`
- **MkDocs documentation** — installation, quick-start, Cortex Agent guide, Cortex Analyst guide, thread management guide, chart plotting guide, and full API reference
- **Comprehensive examples** — runnable scripts in `examples/` covering sync, async, streaming, multi-turn, charts, and Streamlit

### Security

- Account URL validation — enforces HTTPS and validates the Snowflake domain on construction
- URL path-segment percent-encoding in `BaseAgent._get_url()` — prevents URL-injection via agent or schema names
- Credentials loaded exclusively from environment variables or `.env` files; never hard-coded defaults

[Unreleased]: https://github.com/chx5/snowflake-cortex-agents/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/chx5/snowflake-cortex-agents/releases/tag/v0.1.0
