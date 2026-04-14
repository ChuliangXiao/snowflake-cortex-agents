# Snowflake Cortex Agents Documentation

Welcome to the **Snowflake Cortex Agents** SDK documentation! This SDK provides Python clients for interacting with Snowflake's Cortex REST API, including support for Cortex Agents and Analysts powered by Cortex LLMs.

## Quick Links

- **GitHub Repository**: [Snowflake Cortex Agents](https://github.com/ChuliangXiao/snowflake-cortex-agents)
- **Snowflake Cortex Agents**: [Cortex Agents Docs](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents)
- **PyPI Package**: [snowflake-cortex-agents](https://pypi.org/project/snowflake-cortex-agents/)

## Key Capabilities

- 🤖 **Cortex Agent** - Build intelligent agents with Snowflake's Cortex API
- 📊 **Cortex Analyst** - Generate SQL from natural language questions
- ⚡ **Async Support** - Full async/await support for high-performance applications
- 🔄 **Streaming Responses** - Real-time event streaming for interactive experiences
- 🛠️ **Type Hints** - Full type annotations for IDE support and type checking

## Installation

```bash
pip install snowflake-cortex-agents
```

## Quick Start

Setup Snowflake credentials as environment variables:

```bash
export SNOWFLAKE_ACCOUNT_URL=https://your-account.snowflakecomputing.com
export SNOWFLAKE_PAT=your_personal_access_token
```

Or, `pip install snowflake-cortex-agents[dotenv]` and create a `.env` file with your Snowflake credentials. If you're working from this repository, you can copy `.env.example` to `.env` first:

```env
SNOWFLAKE_ACCOUNT_URL=https://your-account.snowflakecomputing.com
SNOWFLAKE_PAT=your_personal_access_token
```

**Synchronous:**

```python
from cortex_agents import CortexAgent

with CortexAgent() as client:
    response = client.run(
        "What's the monthly revenue this year?",
        agent_name="MY_AGENT",
        database="MY_DATABASE",
        schema="MY_SCHEMA"
    )
    for event in response:
        if event["type"] == "text.delta":
            print(event["data"]["text"], end="", flush=True)
```

**Asynchronous:**

```python
import asyncio
from cortex_agents import AsyncCortexAgent

async def main():
    async with AsyncCortexAgent() as agent:
        response = await agent.run(
            "Analyze sales trends",
            agent_name="my_agent"
        )
        for event in response:
            if event["type"] == "text.delta":
                print(event["data"]["text"], end="", flush=True)

asyncio.run(main())
```

## Get Started

Learn more by exploring the documentation sections:

- [Installation](installation.md) - Setup and configuration
- [Quick Start](quickstart.md) - Get started in 5 minutes
- [Examples](guides/agents.md) - Real-world usage examples
- [Cortex Analyst Guide](guides/analyst.md) - Analyst workflows and SQL generation
- [API Reference](api/agent.md) - Complete API documentation
