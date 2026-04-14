# Snowflake Cortex Agents Python SDK

Python SDK for Snowflake Cortex Agents and Cortex Analyst, with sync and async clients, SSE streaming, and chart helpers for agent responses.

## Installation

Install from PyPI:

```bash
pip install snowflake-cortex-agents
```

Optional extras:

- `dotenv` for `.env` loading
- `charts` for Altair and Pandas chart rendering
- `all` for all optional dependencies

```bash
pip install snowflake-cortex-agents[all]
```

For source and contributor setup, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Credentials

Set credentials with environment variables:

```bash
export SNOWFLAKE_ACCOUNT_URL=https://your-account.snowflakecomputing.com
export SNOWFLAKE_PAT=your-personal-access-token
```

Or install `snowflake-cortex-agents[dotenv]` and use a `.env` file:

```env
SNOWFLAKE_ACCOUNT_URL=https://your-account.snowflakecomputing.com
SNOWFLAKE_PAT=your-personal-access-token
```

When working from this repository, you can copy [.env.example](.env.example) to `.env` and fill in your values.

## Quick Start

Both Cortex Agent `run()` and Cortex Analyst `message()` return streaming SSE responses.

### Run an existing agent

```python
from cortex_agents import CortexAgent

with CortexAgent() as client:
    response = client.run(
        "What's this month revenue?",
        agent_name="MY_AGENT",
        database="MY_DATABASE",
        schema="MY_SCHEMA",
    )

    for event in response:
        if event["type"] == "text.delta":
            print(event["data"]["text"], end="", flush=True)
```

### Ask Cortex Analyst a question

```python
from cortex_agents import CortexAnalyst

with CortexAnalyst() as analyst:
    response = analyst.message(
        question="What were the top 5 products by revenue last month?",
        semantic_model_file="@my_stage/semantic_model.yaml",
    )

    for event in response:
        if event["type"] == "text.delta":
            print(event["data"]["text"], end="", flush=True)
        elif event["type"] == "sql.delta":
            print(event["data"]["sql"], end="", flush=True)
```

### Async support

Async clients are available via `AsyncCortexAgent` and `AsyncCortexAnalyst`. See [docs/quickstart.md](docs/quickstart.md) and [examples/example_agent_async.py](examples/example_agent_async.py) for runnable async examples.

## Documentation

- [docs/installation.md](docs/installation.md): installation, optional extras, and credential setup
- [docs/quickstart.md](docs/quickstart.md): sync and async getting-started flows
- [docs/guides/agents.md](docs/guides/agents.md): Cortex Agent usage
- [docs/guides/analyst.md](docs/guides/analyst.md): Cortex Analyst usage
- [docs/guides/threads_api.md](docs/guides/threads_api.md): thread management
- [docs/guides/agents_threads.md](docs/guides/agents_threads.md): conversational agent patterns
- [USAGE.md](USAGE.md): broader API usage notes
- [docs/guides/chart_plotting.md](docs/guides/chart_plotting.md): chart rendering helpers
- [examples/](examples/): runnable examples

## Requirements

- Python 3.10+
- Snowflake account with Cortex enabled
- Personal Access Token (PAT)

## Contributing

Development workflow, uv-based setup, and quality checks are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
