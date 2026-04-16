# Examples

This page showcases various usage patterns and real-world examples.

## Basic Agent Example

```python
from cortex_agents import CortexAgent

# Simple agent query
with CortexAgent() as agent:
    response = agent.run(
        query="What was the revenue last quarter?",
        agent_name="financial_agent",
        database="ANALYTICS",
        schema="FINANCE"
    )

    print(response.text)
    print(f"Generated SQL: {response.sql}")
```

## Streaming Real-time Responses

```python
from cortex_agents import CortexAgent

with CortexAgent() as agent:
    response = agent.run(
        "Analyze customer trends",
        agent_name="analytics_agent"
    )

    # Stream events as they arrive
    for event in response:
        event_type = event["type"]

        if event_type == "text.delta":
            # Real-time text streaming
            print(event["data"]["text"], end="", flush=True)

        elif event_type == "thinking.delta":
            # Agent is thinking
            print(f"\n[Thinking] {event['data']['text']}")

        elif event_type == "tool_use":
            # Agent is using a tool
            tool_name = event["data"]["name"]
            print(f"\n[Using tool: {tool_name}]")
```

## Multi-turn Conversation

```python
from cortex_agents import CortexAgent

with CortexAgent() as agent:
    # Create a thread to hold conversation context
    thread = agent.create_thread()
    thread_id = thread["thread_id"]

    # First question
    response1 = agent.run(
        query="What is our top product?",
        agent_name="sales_agent",
        database="SALES_DB",
        schema="ANALYTICS",
        thread_id=thread_id,
        parent_message_id=0,  # root of thread
    )
    print(f"Answer 1: {response1.text}")

    # Follow-up — agent retains full context via thread
    response2 = agent.run(
        query="How many units did we sell last month?",
        agent_name="sales_agent",
        database="SALES_DB",
        schema="ANALYTICS",
        thread_id=thread_id,
        parent_message_id=response1.message_id,
    )
    print(f"Answer 2: {response2.text}")
```

## Passing Conversation History

For stateless multi-turn without server-side threads, pass prior messages directly via the `messages` argument. You are responsible for building and maintaining the history array.

```python
from cortex_agents import CortexAgent

with CortexAgent() as agent:
    # First turn
    response1 = agent.run(
        query="What is our top product?",
        agent_name="sales_agent",
        database="SALES_DB",
        schema="ANALYTICS",
    )
    print(response1.text)

    # Build history manually from the previous exchange
    history = [
        {"role": "user", "content": [{"type": "text", "text": "What is our top product?"}]},
        {"role": "assistant", "content": [{"type": "text", "text": response1.text}]},
    ]

    # Second turn — agent sees the prior exchange
    response2 = agent.run(
        query="How many units did we sell last month?",
        agent_name="sales_agent",
        database="SALES_DB",
        schema="ANALYTICS",
        messages=history,
    )
    print(response2.text)
```

Use threads (`thread_id` + `message_id`) when you want the server to manage history automatically. Use `messages` when you need full control over what context is sent, or when running ephemeral (inline-config) agents.

## Async Agent with Concurrent Queries

```python
import asyncio
from cortex_agents import AsyncCortexAgent

async def run_queries():
    async with AsyncCortexAgent() as agent:
        # Run multiple queries concurrently
        tasks = [
            agent.run("What is total revenue?", agent_name="agent1"),
            agent.run("What is customer count?", agent_name="agent2"),
            agent.run("What is churn rate?", agent_name="agent3"),
        ]

        results = await asyncio.gather(*tasks)

        for i, result in enumerate(results):
            print(f"Query {i+1}: {result.text}")

asyncio.run(run_queries())
```

## SQL Generation with Analyst

```python
from cortex_agents import CortexAnalyst

with CortexAnalyst() as analyst:
    # Generate SQL from natural language
    response = analyst.message(
        question="Show me the top 10 products by revenue",
        semantic_model_file="@my_stage/products_model.yaml"
    )

    print(f"Question: {response.text}")
    print(f"Generated SQL:\n{response.sql}")
    print(f"Explanation: {response.sql_explanation}")
```

## Multi-model Selection with Analyst

```python
from cortex_agents import CortexAnalyst

with CortexAnalyst() as analyst:
    # Let Analyst choose the best model
    response = analyst.message(
        question="Compare quarterly performance",
        semantic_models=[
            {"semantic_view": "ANALYTICS.PUBLIC.SALES_VIEW"},
            {"semantic_view": "ANALYTICS.PUBLIC.METRICS_VIEW"},
            {"semantic_model_file": "@stage/custom_model.yaml"}
        ]
    )

    print(f"Selected model: {response.semantic_model_selection}")
    print(f"SQL: {response.sql}")
```

## Working with Suggestions

```python
from cortex_agents import CortexAnalyst

with CortexAnalyst() as analyst:
    response = analyst.message(
        question="Revenue by region",
        semantic_model_file="@stage/model.yaml"
    )

    # If ambiguous, get suggestions
    if response.suggestions:
        print("Ambiguous question. Did you mean:")
        for i, suggestion in enumerate(response.suggestions, 1):
            print(f"{i}. {suggestion}")
```

## Handling Charts

```python
from cortex_agents import CortexAgent
from cortex_agents.chart_utils import plot_charts, get_chart_info

with CortexAgent() as agent:
    response = agent.run(
        "Create a monthly revenue chart",
        agent_name="analytics_agent"
    )

    charts = response.get_charts()

    if charts:
        # Get chart metadata without rendering
        info = get_chart_info(charts)
        for chart in info:
            print(f"Chart: {chart['title']}")
            print(f"Type: {chart['mark']}")
            print(f"Fields: {chart['fields']}")

        # Render charts
        plot_charts(charts, interactive=True)
```

## Error Handling

```python
from cortex_agents import CortexAgent
from cortex_agents.base import SnowflakeAPIError

try:
    with CortexAgent() as agent:
        response = agent.run(
            "Your question",
            agent_name="my_agent"
        )
except SnowflakeAPIError as e:
    print(f"API Error: {e.message}")
    print(f"Status: {e.status_code}")
    print(f"Request ID: {e.request_id}")
    if e.response_body:
        print(f"Response: {e.response_body}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Feedback Submission

```python
from cortex_agents import CortexAgent

with CortexAgent() as agent:
    response = agent.run(
        "Your question",
        agent_name="my_agent"
    )

    # Submit feedback about the response
    agent.submit_feedback(
        agent_name="my_agent",
        database="MY_DB",
        schema="MY_SCHEMA",
        positive=True,
        orig_request_id=response.request_id,
        feedback_message="Great answer, very helpful!",
    )
```

## Streaming in Streamlit

```python
import streamlit as st
from cortex_agents import CortexAgent

st.title("AI Agent Demo")

query = st.text_input("Ask a question:")

if query:
    with CortexAgent() as agent:
        response = agent.run(query, agent_name="my_agent", database="MY_DB", schema="MY_SCHEMA")

        # Stream response to Streamlit
        placeholder = st.empty()
        text = ""

        for event in response:
            if event["type"] == "text.delta":
                text += event["data"]["text"]
                placeholder.write(text)

        # Show charts if any
        charts = response.get_charts()
        if charts:
            from cortex_agents.chart_utils import plot_charts
            plot_charts(charts)
```

## Inline Agent Runs (Ephemeral Config)

Run an agent without a pre-created agent object using `AgentInlineConfig`:

```python
from cortex_agents import CortexAgent, AgentInlineConfig

with CortexAgent() as agent:
    response = agent.run(
        query="Summarize the quarterly results",
        agent_config=AgentInlineConfig(
            models={"orchestration": "claude-sonnet-4-6"},
            instructions={"system": "You are a concise financial analyst"},
            tools=[{"tool_spec": {"type": "cortex_analyst_text2sql", "name": "analyst"}}],
            tool_resources={"analyst": {"semantic_view": "DB.SCHEMA.SALES_VIEW"}},
        ),
    )
    print(response.text)
```

No `agent_name`, `database`, or `schema` are needed — the config is sent inline with the request.

## List Available Models

```python
with CortexAgent() as agent:
    models = agent.list_models()
    print(models)
```

## Working with Response Properties

`AgentResponse` exposes accessors beyond `text` and `sql`:

```python
response = agent.run(query="Analyze sales", agent_name="MY_AGENT", database="DB", schema="SCH")

# SQL and related data
print(response.sql)               # SQL from Cortex Analyst tool
print(response.sql_explanation)   # Analyst's explanation of the SQL
print(response.query_id)          # Snowflake query ID for the SQL execution
result = response.get_sql_result()
if result:
    print(result["data"])         # rows; result["resultSetMetaData"] for schema

# Thinking / reasoning (extended thinking models)
print(response.thinking)

# Thread continuity
print(response.message_id)        # use as parent_message_id in next run
print(response.run_id)

# Metadata
usage = response.get_token_usage()
if usage:
    print(f"Tokens consumed: {usage.get('tokens_consumed')}")

# Warnings and suggestions
for warning in response.get_warnings():
    print(f"Warning: {warning}")
for suggestion in response.get_suggested_queries():
    print(f"Suggestion: {suggestion}")

# Annotations (citations, references)
annotations = response.get_annotations()

# Elicitation (agent asking for more info)
if response.is_elicitation:
    print("Agent needs more information")

# Raw event list (after streaming)
all_events = response.events
```

## More Examples

Check out the [examples/](https://github.com/chx5/snowflake-cortex-agents/tree/main/examples) directory in the repository for complete, runnable examples.
