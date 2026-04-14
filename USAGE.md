# Snowflake Cortex Agents SDK - Usage Guide

## Installation

```python
from cortex_agents import CortexAgent
```

## Quick Start

### 1. Initialize the Client

```python
# Option 1: Use environment variables (recommended)
# Set SNOWFLAKE_ACCOUNT_URL and SNOWFLAKE_PAT in your .env file
client = CortexAgent()

# Option 2: Explicit credentials
client = CortexAgent(
    account_url="https://your-account.snowflakecomputing.com",
    pat="your_personal_access_token"
)
```

**Note:** Database and schema are now specified per operation, not at initialization.

### 2. Create an Agent

```python
# Simple agent with basic configuration
client.create_agent(
    name="SALES_AGENT",
    config={
        "instructions": {
            "system": "You are a sales analyst. Help users understand sales data."
        },
        "models": {
            "orchestration": "claude-sonnet-4-6"
        }
    },
    database="MY_DATABASE",
    schema="MY_SCHEMA"
)
```

**Full configuration example:**

```python
client.create_agent(
    name="ADVANCED_AGENT",
    config={
        "instructions": {
            "system": "You are an expert data analyst.",
            "profile": "Provide detailed explanations with data."
        },
        "models": {
            "orchestration": "claude-sonnet-4-6",
            "query_writer": "mistral-large2"
        },
        "tools": [
            {
                "type": "builtin_function",
                "name": "QUERY_WAREHOUSE"
            },
            {
                "type": "builtin_function",
                "name": "PYTHON_CODE_EXECUTOR",
                "spec": {
                    "handler": "MY_HANDLER_FUNCTION",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"}
                        }
                    }
                }
            }
        ],
        "budget": {
            "orchestration_tokens": 100000,
            "context_window_tokens": 50000
        }
    },
    database="MY_DATABASE",
    schema="MY_SCHEMA"
)
```

### 3. Run the Agent

**Simple query:**

```python
response = client.run(
    "What was our total revenue last quarter?",
    agent_name="SALES_AGENT",
    database="MY_DATABASE",
    schema="MY_SCHEMA"
)

# Access results directly
print(response.text)        # Natural language answer
print(response.sql)         # SQL query used (if any)
print(response.thinking)    # Agent's reasoning process
```

**With additional configuration:**

```python
response = client.run(
    "Compare Q1 vs Q2 sales by region",
    agent_name="SALES_AGENT",
    semantic_model_file="@sales_models/revenue_model.yaml",
    temperature=0.7,
    thread_id="my-conversation-thread",
    parent_message_id=0,
)
```

**Custom message payload:**

```python
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "Summarize revenue by region"},
            {"type": "table", "table": {...}},  # Additional content types supported by the API
        ],
    }
]

response = client.run(
    query="",  # Ignored when messages is provided
    agent_name="SALES_AGENT",
    messages=messages,
)
```

### 4. Stream Results

```python
response = agent.run("Analyze customer trends", agent_name="SALES_AGENT")

# Response is directly iterable
for event in response:
    event_type = event["type"]
    data = event["data"]

    if event_type == "text.delta":
        print(data["text"], end="", flush=True)
    elif event_type == "sql.delta":
        print(f"\nSQL: {data['sql']}")
    elif event_type == "thinking.delta":
        print(f"Thinking: {data['thinking']}")
    elif event_type == "chart":
        print(f"Chart generated: {data}")
    elif event_type == "table":
        print(f"Table data: {data}")

# Note: response.stream() also works for backward compatibility
```

### 5. Access Response Components

```python
response = agent.run("Show top 10 customers", agent_name="SALES_AGENT")

# Get all component types
charts = response.get_charts()
tables = response.get_tables()
tool_uses = response.get_tool_uses()

# Access raw metadata
metadata = response.get_metadata()
print(f"Request ID: {metadata.get('x-snowflake-request-id')}")
```

## Tool Selection

Control which tools an agent can use with the `tool_choice` parameter.

### Auto Selection (Default)

Allows the agent to automatically choose which tools to use:

```python
# These are equivalent:
response = agent.run("What's the revenue?", agent_name="SALES_AGENT")

response = agent.run(
    "What's the revenue?",
    agent_name="SALES_AGENT",
    tool_choice={"type": "auto"}
)
```

### Required Tool Usage

Force the agent to use at least one tool:

```python
response = agent.run(
    "Analyze the sales data",
    agent_name="SALES_AGENT",
    tool_choice={"type": "required"}
)
```

### Specific Tool Selection

Restrict the agent to specific tools:

```python
response = agent.run(
    "Query the database",
    agent_name="SALES_AGENT",
    tool_choice={
        "type": "tool",
        "name": ["QUERY_WAREHOUSE", "PYTHON_CODE_EXECUTOR"]
    }
)
```

## Response Metadata

Access important information from agent and analyst responses for tracking and feedback.

### Agent Response Properties

```python
response = agent.run("What's the revenue?", agent_name="SALES_AGENT")

# Request tracking
print(f"Request ID: {response.request_id}")           # For feedback
print(f"Message ID: {response.message_id}")           # For thread continuity

# Response content
print(f"Text: {response.text}")                       # Natural language
print(f"SQL: {response.sql}")                         # SQL executed
print(f"Thinking: {response.thinking}")               # Reasoning
print(f"Query ID: {response.query_id}")               # Snowflake query ID

# Response structure
charts = response.charts                             # Chart data
tables = response.tables                             # Table results
tool_uses = response.tool_uses                       # Tool invocations
```

### Analyst Response Properties

```python
response = analyst.message(
    "Which products had the most revenue?",
    semantic_model_file="@models/revenue_model.yaml"
)

# Request tracking
print(f"Request ID: {response.request_id}")           # For feedback

# Generated SQL
print(f"SQL: {response.sql}")                        # Generated SQL statement
print(f"Text: {response.text}")                      # Interpretation

# Query verification
if response.verified_query_used:
    vq = response.verified_query_used
    print(f"Verified Query Name: {vq['name']}")
    print(f"Original Question: {vq['question']}")
    print(f"Verified By: {vq['verified_by']}")
    print(f"Verified At: {vq['verified_at']}")

# Confidence and explanation
print(f"Confidence: {response.confidence}")           # Confidence metadata
print(f"SQL Explanation: {response.sql_explanation}") # How SQL was generated
print(f"Semantic Model: {response.semantic_model_selection}")  # Model used

# Results
if response.result_set:
    print(f"Results: {response.result_set['data']}")  # Execution results

# Suggestions for ambiguous questions
if response.suggestions:
    print("Did you mean:")
    for suggestion in response.suggestions:
        print(f"  - {suggestion}")

# Response metadata
print(f"Warnings: {response.warnings}")               # Any warnings
print(f"Metadata: {response.response_metadata}")      # Full metadata
```

## Thread Management

### Create and Use Threads

```python
# Create a conversation thread with optional origin_app (max 16 bytes)
thread_id = agent.create_thread(origin_app="my_app")["thread_id"]

# Run multiple queries in the same thread (maintains context)
response1 = agent.run(
    "What's our revenue?",
    agent_name="SALES_AGENT",
    thread_id=thread_id,
    parent_message_id=0,  # First turn must use parent_message_id=0
)

# Use the assistant message ID from the prior response for follow-up turns
response2 = agent.run(
    "How does that compare to last year?",  # Context maintained
    agent_name="SALES_AGENT",
    thread_id=thread_id,
    parent_message_id=response1.message_id,
)

# Get thread history
thread = agent.get_thread(thread_id)
print(f"Messages in thread: {len(thread['messages'])}")

# List all threads
threads = agent.list_threads()
for thread in threads:
    print(f"Thread {thread['id']}: {thread['created_at']}")

# Clean up
agent.delete_thread(thread_id)
```

## Agent Management

### List and Update Agents

```python
# List all agents
agents = agent.list_agents()
for agent in agents:
    print(f"Agent: {agent['name']}")

# Get specific agent details
agent = agent.get_agent("SALES_AGENT")
print(agent['config'])

# Update agent configuration
agent.update_agent(
    "SALES_AGENT",
    config={
        "instructions": {
            "system": "Updated instructions"
        }
    }
)

# Delete an agent
agent.delete_agent("SALES_AGENT")
```

## Run Without an Agent

For one-off queries without creating a persistent agent:

```python
response = agent.run(
    "Calculate average order value",
    config={
        "instructions": {"system": "You are a sales analyst."},
        "models": {"orchestration": "claude-sonnet-4-6"}
    }
)

print(response.text)
```

## Feedback Collection

Submit feedback about agent responses to help improve agent performance:

### Request-Level Feedback

```python
# Run an agent and collect feedback on the specific response
response = agent.run("What was our Q1 revenue?", agent_name="SALES_AGENT")

# User likes the response
agent.submit_feedback(
    agent_name="SALES_AGENT",
    positive=True,
    orig_request_id=response.request_id,  # Link to specific response
    feedback_message="Very accurate and helpful!",
    categories=["Something worked well", "Accurate data"]
)

# User dislikes the response
agent.submit_feedback(
    agent_name="SALES_AGENT",
    positive=False,
    orig_request_id=response.request_id,
    feedback_message="Wrong time period",
    categories=["Wrong answer"]
)
```

### Agent-Level Feedback

```python
# General feedback about the agent (no request_id)
agent.submit_feedback(
    agent_name="SALES_AGENT",
    positive=True,
    feedback_message="Great agent overall!",
    categories=["Something worked well"]
)
```

### Feedback with Thread Context

```python
# Feedback on a threaded conversation
thread_id = agent.create_thread()["thread_id"]
response = agent.run(
    "Show revenue trends",
    agent_name="SALES_AGENT",
    thread_id=thread_id,
    parent_message_id=0,  # Start of conversation thread
)

agent.submit_feedback(
    agent_name="SALES_AGENT",
    positive=True,
    orig_request_id=response.request_id,
    thread_id=thread_id,
    feedback_message="Understood context well"
)
```

## Error Handling

```python
from cortex_agents import CortexAgent, SnowflakeAPIError

agent = CortexAgent()

try:
    response = agent.run("query", agent_name="NONEXISTENT", database="MY_DB", schema="MY_SCHEMA")
except SnowflakeAPIError as e:
    print(f"Error {e.status_code}: {e.message}")
    print(f"Request ID: {e.request_id}")
```

## Complete Example

```python
from cortex_agents import CortexAgent

# Initialize
agent = CortexAgent(
    database="SALES_DB",
    schema="ANALYTICS"
)

# Create agent
agent.create_agent(
    name="REVENUE_ANALYST",
    config={
        "instructions": {
            "system": "Expert sales analyst focused on revenue metrics",
            "profile": "Provide actionable insights with data"
        },
        "models": {
            "orchestration": "claude-sonnet-4-6"
        },
        "tools": [
            {"type": "builtin_function", "name": "QUERY_WAREHOUSE"}
        ]
    }
)

# Create conversation thread
thread_id = agent.create_thread()["thread_id"]

# Interactive conversation
queries = [
    "What was our total revenue last quarter?",
    "Which region performed best?",
    "Show me the top 5 products by revenue"
]

parent_id = 0

for query in queries:
    print(f"\nQuery: {query}")
    response = agent.run(
        query,
        agent_name="REVENUE_ANALYST",
        thread_id=thread_id,
        parent_message_id=parent_id,
    )

    # Iterate directly over the response
    for event in response:
        if event["type"] == "text.delta":
            print(event["data"]["text"], end="", flush=True)

    print("\n" + "="*50)
    if response.message_id is not None:
        parent_id = response.message_id

    # Show SQL used
    if response.sql:
        print(f"SQL executed:\n{response.sql}")

# Cleanup
agent.delete_thread(thread_id)
```

## Configuration Options

### Agent Config Dictionary

```python
{
    "instructions": {
        "system": str,      # Required: System instructions
        "profile": str      # Optional: Agent profile/personality
    },
    "models": {
        "orchestration": str,          # Required: Main reasoning model
        "query_writer": str,           # Optional: SQL generation model
        "context_window_tokens": int   # Optional: Context window size
    },
    "tools": [                         # Optional: Available tools
        {
            "type": "builtin_function",
            "name": str,
            "spec": dict,              # Optional: Tool specification
            "resources": [dict]        # Optional: Tool resources
        }
    ],
    "budget": {                        # Optional: Resource limits
        "orchestration_tokens": int,
        "context_window_tokens": int
    },
    "execution_environment": {         # Optional: Execution settings
        "warehouse": str
    }
}
```

### Run Parameters

- `query` (str): The user query or prompt
- `agent_name` (str, optional): Name of agent to use
- `config` (dict, optional): Inline agent config (if not using named agent)
- `thread_id` (str, optional): Thread ID for conversation context
- `semantic_model_file` (str, optional): Path to semantic model file
- `temperature` (float, optional): Model temperature (0.0-1.0)
- Any other parameters supported by the Snowflake API

### Feedback Parameters

- `agent_name` (str): Name of the agent
- `positive` (bool): True for positive feedback, False for negative
- `feedback_message` (str, optional): Detailed feedback text
- `categories` (list[str], optional): Feedback categories (e.g., ["Something worked well"])
- `orig_request_id` (str, optional): Request ID for request-level feedback (from `response.request_id`)
- `thread_id` (str, optional): Thread ID if feedback is for threaded conversation
- `database` (str, optional): Override default database
- `schema` (str, optional): Override default schema

## Event Types

When streaming, you'll receive events with these types:

- `"text.delta"` - Incremental text response
- `"sql.delta"` - Incremental SQL query
- `"thinking.delta"` - Agent's reasoning process
- `"sql_explanation.delta"` - SQL explanation
- `"chart"` - Chart visualization data
- `"table"` - Table data results
- `"tool_use"` - Tool invocation details
- `"message.completed"` - Final message with complete data

Access event data via `event["data"]` dictionary.
