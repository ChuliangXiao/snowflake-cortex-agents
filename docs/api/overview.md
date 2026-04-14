# API Reference Overview

The Snowflake Cortex Agents SDK provides Python clients for interacting with Snowflake's Cortex Agents and Cortex Analyst APIs.

## Main Components

### Client Classes

The SDK provides both synchronous and asynchronous clients:

- **[CortexAgent](agent.md)** - Synchronous client for Cortex Agents API
- **[AsyncCortexAgent](async_agent.md)** - Asynchronous client for Cortex Agents API
- **[CortexAnalyst](analyst.md)** - Synchronous client for Cortex Analyst API
- **[AsyncCortexAnalyst](async_analyst.md)** - Asynchronous client for Cortex Analyst API

### Response Classes

Response wrappers provide convenient access to API results:

- **[AgentResponse](response.md#agentresponse)** - Wrapper for agent run responses with streaming support
- **[AnalystResponse](response.md#analystresponse)** - Wrapper for analyst message responses
- **[EventType](response.md#eventtype)** - Enumeration of SSE event types

### Core Modules

Advanced users can access lower-level components:

- **[Entity Management](core_entity.md)** - Create, read, update, and delete agents
- **[Run Management](core_run.md)** - Execute agent runs
- **[Thread Management](core_threads.md)** - Manage conversation threads
- **[Feedback Management](core_feedback.md)** - Submit user feedback

### Utilities

Helper functions and base classes:

- **[Base Classes](base.md)** - Base agent class and exceptions
- **[Chart Utilities](chart_utils.md)** - Chart plotting helpers
- **[Utils](utils.md)** - Credential loading and validation

## Quick Start

### Cortex Agent

```python
from cortex_agents import CortexAgent

# Initialize client
with CortexAgent() as agent:
    # Create an agent
    agent.create_agent(
        name="MY_AGENT",
        config={
            "instructions": {"system": "You are helpful"},
            "models": {"orchestration": "claude-sonnet-4-6"}
        },
        database="MY_DB",
        schema="MY_SCHEMA"
    )

    # Run the agent
    response = agent.run(
        "What's the revenue?",
        agent_name="MY_AGENT",
        database="MY_DB",
        schema="MY_SCHEMA"
    )

    # Access results
    print(response.text)
    print(response.sql)
```

### Cortex Analyst

```python
from cortex_agents import CortexAnalyst

# Initialize client
analyst = CortexAnalyst()

# Generate SQL from natural language
response = analyst.message(
    "Which company had the most revenue?",
    semantic_model_file="@my_stage/model.yaml"
)

# Access results
print(response.text)  # Natural language interpretation
print(response.sql)   # Generated SQL query
```

## Key Features

- **Streaming Support**: All run/message methods support SSE streaming for real-time responses
- **Context Management**: Automatic resource cleanup with context managers
- **Thread Management**: Multi-turn conversations with thread support
- **Feedback Collection**: Submit user feedback on agent responses
- **Type Hints**: Full type annotations for better IDE support
- **Async Support**: Complete async/await API with AsyncCortexAgent and AsyncCortexAnalyst

## Error Handling

All API errors raise `SnowflakeAPIError`:

```python
from cortex_agents import CortexAgent, SnowflakeAPIError

try:
    with CortexAgent() as agent:
        response = agent.run("test", agent_name="MY_AGENT", database="DB", schema="SCHEMA")
except SnowflakeAPIError as e:
    print(f"API Error: {e}")
```

## Authentication

The SDK supports two authentication methods:

1. **Environment Variables** (recommended):
   ```bash
   export SNOWFLAKE_ACCOUNT_URL="https://your-account.snowflakecomputing.com"
   export SNOWFLAKE_PAT="your-personal-access-token"
   ```

2. **Direct Parameters**:
   ```python
   agent = CortexAgent(
       account_url="https://your-account.snowflakecomputing.com",
       pat="your-personal-access-token"
   )
   ```

## Next Steps

- See [Examples](../guides/agents.md) for detailed usage examples
- Read [Quick Start](../quickstart.md) for getting started guide
- Explore the [Main Classes](#client-classes) documentation
