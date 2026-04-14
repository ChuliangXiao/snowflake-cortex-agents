# Quick Start

This guide will get you up and running with Snowflake Cortex Agents in 5 minutes.

## Prerequisites

- Python 3.10+
- Snowflake account with Cortex API access
- Personal Access Token (PAT)
- An agent defined in your Snowflake account

## Set Up Credentials

Create a `.env` file in your project:

```ini
SNOWFLAKE_ACCOUNT_URL=https://your-account.snowflakecomputing.com
SNOWFLAKE_PAT=your-personal-access-token
```

## Install the SDK

```bash
pip install snowflake-cortex-agents
```

## Basic Agent Usage

### Synchronous Example

```python
from cortex_agents import CortexAgent

# Use context manager for automatic cleanup
with CortexAgent() as agent:
    # Run an agent
    response = agent.run(
        query="What is the total revenue?",
        agent_name="my_agent",
        database="MY_DATABASE",
        schema="MY_SCHEMA"
    )

    # Access results
    print(f"Answer: {response.text}")
    print(f"Request ID: {response.request_id}")
```

### Asynchronous Example

```python
import asyncio
from cortex_agents import AsyncCortexAgent

async def main():
    async with AsyncCortexAgent() as agent:
        response = await agent.run(
            query="What is the total revenue?",
            agent_name="my_agent",
            database="MY_DATABASE",
            schema="MY_SCHEMA"
        )
        print(response.text)

asyncio.run(main())
```

## Streaming Responses

Stream real-time events as they're generated:

```python
from cortex_agents import CortexAgent

with CortexAgent() as agent:
    response = agent.run("Your question here", agent_name="my_agent", database="my_db", schema="my_schema")

    # Stream events in real-time
    for event in response:
        if event["type"] == "text.delta":
            print(event["data"]["text"], end="", flush=True)
        elif event["type"] == "tool_use":
            print(f"\n[Using tool: {event['data']['name']}]")
```

## Using Cortex Analyst

Generate SQL from natural language:

```python
from cortex_agents import CortexAnalyst

with CortexAnalyst() as analyst:
    response = analyst.message(
        question="Show top 10 customers by revenue",
        semantic_model_file="@my_stage/customer_model.yaml"
    )

    print(f"SQL Generated: {response.sql}")
    print(f"Interpretation: {response.text}")
```

## Working with Charts

If your agent generates charts:

```python
from cortex_agents import CortexAgent
from cortex_agents.chart_utils import plot_charts

with CortexAgent() as agent:
    response = agent.run(
        "Create a sales trend chart",
        agent_name="my_agent"
    )

    charts = response.get_charts()
    if charts:
        plot_charts(charts)  # Renders in Jupyter/IPython
```

## Common Patterns

### Multi-turn Conversation

```python
from cortex_agents import CortexAgent

with CortexAgent() as agent:
    # Create a thread for multi-turn context
    thread = agent.create_thread()
    thread_id = thread["thread_id"]

    # First question
    response1 = agent.run("What is revenue?", agent_name="my_agent", database="my_db", schema="my_schema",
                          thread_id=thread_id, parent_message_id=0)
    print(response1.text)

    # Follow-up — agent retains context via thread
    response2 = agent.run(
        "How does it compare to last year?",
        agent_name="my_agent",
        database="my_db",
        schema="my_schema",
        thread_id=thread_id,
        parent_message_id=response1.message_id,
    )
    print(response2.text)
```

### Error Handling

```python
from cortex_agents import CortexAgent
from cortex_agents.base import SnowflakeAPIError

try:
    with CortexAgent() as agent:
        response = agent.run("Your question", agent_name="my_agent", database="my_db", schema="my_schema")
except SnowflakeAPIError as e:
    print(f"API Error: {e.message}")
    print(f"Status Code: {e.status_code}")
    print(f"Request ID: {e.request_id}")
```

## Next Steps

- Read the [API Reference](api/agent.md) for complete API details
- Explore more [Examples](guides/agents.md)
- Check out [Snowflake's Cortex documentation](https://docs.snowflake.com/)
