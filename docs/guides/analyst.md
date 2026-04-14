# Cortex Analyst Guide

Comprehensive guide to using Snowflake Cortex Analyst for SQL generation from natural language.

## Overview

Cortex Analyst is a powerful feature that translates natural language questions into SQL queries using semantic models. It's perfect for:

- **Business Intelligence**: Enable non-technical users to query data
- **Data Exploration**: Quickly explore datasets without writing SQL
- **Report Generation**: Automate SQL query creation for reports
- **Conversational Analytics**: Build chat-based data applications

## Quick Start

### Basic SQL Generation

```python
from cortex_agents import CortexAnalyst

# Initialize analyst
with CortexAnalyst() as analyst:
    response = analyst.message(
        question="Which company had the most revenue?",
        semantic_model_file="@my_stage/revenue_model.yaml"
    )

    print(f"Interpretation: {response.text}")
    print(f"Generated SQL:\n{response.sql}")
```

### Using Semantic Views

```python
with CortexAnalyst() as analyst:
    response = analyst.message(
        question="Show top 10 customers by revenue",
        semantic_view="MY_DB.MY_SCHEMA.CUSTOMER_VIEW"
    )

    print(response.sql)
```

## Semantic Models vs Views

### Semantic Model Files

Semantic model files are YAML files stored in Snowflake stages that define:
- Table relationships
- Column semantics
- Business logic
- Aggregation rules

```python
response = analyst.message(
    question="What's the year-over-year growth?",
    semantic_model_file="@analytics.public.models/sales_model.yaml"
)
```

### Semantic Views

Semantic views are Snowflake objects that embed semantic information directly:

```python
response = analyst.message(
    question="Top performing regions",
    semantic_view="ANALYTICS.PUBLIC.SALES_SEMANTIC_VIEW"
)
```

## Multi-Model Selection

Let Analyst automatically choose the best model for your question:

```python
response = analyst.message(
    question="Analyze customer purchase patterns across regions",
    semantic_models=[
        {"semantic_view": "ANALYTICS.PUBLIC.CUSTOMER_VIEW"},
        {"semantic_view": "ANALYTICS.PUBLIC.SALES_VIEW"},
        {"semantic_model_file": "@stage/product_model.yaml"}
    ]
)

# Check which model was selected
if response.response_metadata:
    selected = response.response_metadata.get("semantic_model_selection")
    print(f"Selected model: {selected}")
```

## Streaming Responses

Stream SQL generation in real-time:

```python
response = analyst.message(
    question="Calculate monthly revenue trends",
    semantic_view="ANALYTICS.PUBLIC.REVENUE_VIEW"
)

print("Generating SQL...")
for event in response:
    if event["type"] == "status":
        print(f"[{event['data']['status']}]")

    elif event["type"] == "text.delta":
        # Stream interpretation text
        print(event["data"]["text"], end="", flush=True)

    elif event["type"] == "sql.delta":
        # SQL is being generated
        print(f"\n\nSQL:\n{event['data']['sql']}")

    elif event["type"] == "suggestions":
        # Question was ambiguous
        print("\nSuggestions:")
        for suggestion in event["data"]["suggestions"]:
            print(f"  - {suggestion}")

# After streaming, access complete results
print(f"\n\nFinal SQL:\n{response.sql}")
print(f"Interpretation: {response.text}")
```

## Multi-Turn Conversations

Maintain conversation context for follow-up questions:

```python
# First question
response1 = analyst.message(
    question="What was the total revenue last quarter?",
    semantic_view="ANALYTICS.PUBLIC.SALES_VIEW"
)
print(f"Q1: {response1.text}")
print(f"SQL1: {response1.sql}")

# Follow-up question with context
response2 = analyst.message(
    question="How does that compare to the previous quarter?",
    semantic_view="ANALYTICS.PUBLIC.SALES_VIEW",
    messages=response1.conversation_messages  # Pass conversation history
)
print(f"\nQ2: {response2.text}")
print(f"SQL2: {response2.sql}")

# Third question building on context
response3 = analyst.message(
    question="What were the top 3 products?",
    semantic_view="ANALYTICS.PUBLIC.SALES_VIEW",
    messages=response2.conversation_messages
)
print(f"\nQ3: {response3.text}")
print(f"SQL3: {response3.sql}")
```

## Handling Ambiguous Questions

When a question is unclear, Analyst provides suggestions:

```python
response = analyst.message(
    question="revenue",  # Ambiguous
    semantic_view="ANALYTICS.PUBLIC.SALES_VIEW"
)

if response.suggestions:
    print("Your question was ambiguous. Did you mean:")
    for i, suggestion in enumerate(response.suggestions, 1):
        print(f"{i}. {suggestion}")

    # User selects a suggestion, then re-query
    clarified_response = analyst.message(
        question=response.suggestions[0],  # Use first suggestion
        semantic_view="ANALYTICS.PUBLIC.SALES_VIEW"
    )
    print(f"\nSQL: {clarified_response.sql}")
else:
    print(f"SQL: {response.sql}")
```

## Working with Response Properties

### Text and SQL

```python
response = analyst.message(
    question="Total sales by region",
    semantic_view="ANALYTICS.PUBLIC.SALES_VIEW"
)

# Interpretation of the query
print(f"Interpretation: {response.text}")

# Generated SQL query
print(f"SQL:\n{response.sql}")

# SQL explanation (if available)
if response.sql_explanation:
    print(f"Explanation: {response.sql_explanation}")
```

### Confidence Information

```python
response = analyst.message(
    question="Unusual sales patterns last month",
    semantic_view="ANALYTICS.PUBLIC.SALES_VIEW"
)

if response.confidence:
    print(f"Confidence: {response.confidence}")
```

### Warnings

```python
response = analyst.message(
    question="All sales data for all time",
    semantic_view="ANALYTICS.PUBLIC.SALES_VIEW"
)

if response.warnings:
    print("Warnings:")
    for warning in response.warnings:
        print(f"  - {warning.get('message')}")
```

### Request ID

```python
response = analyst.message(
    question="Revenue breakdown",
    semantic_view="ANALYTICS.PUBLIC.SALES_VIEW"
)

# Use request_id for debugging or feedback
print(f"Request ID: {response.request_id}")
```

## Submitting Feedback

Help improve Analyst by submitting feedback:

```python
response = analyst.message(
    question="Top 5 customers by lifetime value",
    semantic_view="ANALYTICS.PUBLIC.CUSTOMER_VIEW"
)

print(f"SQL: {response.sql}")

# Positive feedback
analyst.submit_feedback(
    request_id=response.request_id,
    positive=True,
    feedback_message="Perfect SQL generation!"
)

# Negative feedback with details
analyst.submit_feedback(
    request_id=response.request_id,
    positive=False,
    feedback_message="The SQL didn't handle NULL values correctly"
)
```

## Async Usage

Use async/await for non-blocking operations:

```python
import asyncio
from cortex_agents import AsyncCortexAnalyst

async def analyze_data():
    async with AsyncCortexAnalyst() as analyst:
        # Generate SQL asynchronously
        response = await analyst.message(
            question="Monthly revenue trends",
            semantic_view="ANALYTICS.PUBLIC.SALES_VIEW"
        )

        # Async streaming
        print("Streaming response:")
        async for event in response.astream():
            if event["type"] == "text.delta":
                print(event["data"]["text"], end="", flush=True)

        print(f"\n\nFinal SQL:\n{response.sql}")

asyncio.run(analyze_data())
```

### Concurrent Queries

Run multiple queries in parallel:

```python
async def concurrent_analysis():
    async with AsyncCortexAnalyst() as analyst:
        # Create multiple queries
        tasks = [
            analyst.message("Total revenue", semantic_view="SALES_VIEW"),
            analyst.message("Customer count", semantic_view="CUSTOMER_VIEW"),
            analyst.message("Average order value", semantic_view="ORDER_VIEW")
        ]

        # Execute concurrently
        responses = await asyncio.gather(*tasks)

        for i, response in enumerate(responses, 1):
            print(f"\nQuery {i}:")
            print(f"SQL: {response.sql}")
            print(f"Interpretation: {response.text}")

asyncio.run(concurrent_analysis())
```

## Advanced Patterns

### Retry Logic

The SDK includes automatic retry with exponential backoff for transient errors:

```python
# Automatically retries on 429 (rate limit) and 5xx errors
response = analyst.message(
    question="Complex aggregation query",
    semantic_view="ANALYTICS.PUBLIC.LARGE_VIEW"
)
```

### Timeouts

The SDK uses a 15-minute read timeout by default (sufficient for complex queries). There is no public API to change the timeout after construction — if you need a different value, create a subclass or open an issue.

```python
# Default timeouts: connect=30s, read=900s, write=30s
analyst = CortexAnalyst()
```

### Error Handling

```python
from cortex_agents import CortexAnalyst
from cortex_agents.base import SnowflakeAPIError

try:
    with CortexAnalyst() as analyst:
        response = analyst.message(
            question="Invalid semantic model reference",
            semantic_model_file="@invalid/path.yaml"
        )
except SnowflakeAPIError as e:
    print(f"API Error: {e.message}")
    print(f"Status Code: {e.status_code}")
    print(f"Request ID: {e.request_id}")

    if e.status_code == 404:
        print("Semantic model not found")
    elif e.status_code == 429:
        print("Rate limited, retry later")
    elif e.status_code >= 500:
        print("Server error, retry")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Best Practices

### 1. Be Specific in Questions

❌ **Bad**: "revenue"
✅ **Good**: "What was the total revenue for Q4 2024?"

### 2. Use Conversation Context

For related questions, pass conversation history:

```python
response1 = analyst.message("What was Q1 revenue?", semantic_view="SALES_VIEW")
response2 = analyst.message(
    "What about Q2?",  # Context maintained
    semantic_view="SALES_VIEW",
    messages=response1.conversation_messages
)
```

### 3. Handle Ambiguity Gracefully

```python
response = analyst.message(question=user_input, semantic_view="VIEW")

if response.suggestions:
    # Present suggestions to user for clarification
    show_suggestions_ui(response.suggestions)
else:
    # Execute the generated SQL
    execute_query(response.sql)
```

### 4. Submit Feedback

Help improve the service by submitting feedback on results.

### 5. Use Multi-Model Selection

When unsure which model fits best, let Analyst choose:

```python
response = analyst.message(
    question=complex_question,
    semantic_models=[model1, model2, model3]
)
```

### 6. Monitor Warnings

Check `response.warnings` for potential issues with generated SQL.

### 7. Cache Responses

For repeated questions, consider caching SQL results:

```python
import hashlib
from functools import lru_cache

@lru_cache(maxsize=128)
def get_sql_for_question(question: str, semantic_view: str) -> str:
    with CortexAnalyst() as analyst:
        response = analyst.message(question=question, semantic_view=semantic_view)
        return response.sql
```

## Complete Example

```python
"""
Complete Analyst workflow: question -> SQL -> execution -> feedback
"""
from cortex_agents import CortexAnalyst
from snowflake.connector import connect

def analyze_question(question: str):
    """Analyze a question and return results."""

    # Initialize Analyst
    with CortexAnalyst() as analyst:
        # Generate SQL
        response = analyst.message(
            question=question,
            semantic_view="ANALYTICS.PUBLIC.SALES_VIEW"
        )

        # Handle ambiguity
        if response.suggestions:
            print("Please clarify your question:")
            for i, suggestion in enumerate(response.suggestions, 1):
                print(f"{i}. {suggestion}")
            return None

        # Check warnings
        if response.warnings:
            print("Warnings:")
            for warning in response.warnings:
                print(f"  - {warning.get('message')}")

        print(f"Generated SQL:\n{response.sql}\n")

        # Execute SQL (requires snowflake-connector-python)
        try:
            with connect(
                account="your_account",
                user="your_user",
                password="your_password"
            ) as conn:
                cursor = conn.cursor()
                cursor.execute(response.sql)
                results = cursor.fetchall()

                print(f"Results: {len(results)} rows")
                for row in results[:5]:  # Show first 5
                    print(row)

                # Positive feedback on success
                analyst.submit_feedback(
                    request_id=response.request_id,
                    positive=True,
                    feedback_message="Query executed successfully"
                )

                return results

        except Exception as e:
            print(f"Execution error: {e}")

            # Negative feedback on failure
            analyst.submit_feedback(
                request_id=response.request_id,
                positive=False,
                feedback_message=f"SQL execution failed: {str(e)}"
            )
            return None

# Use it
analyze_question("What were the top 5 products by revenue last quarter?")
```

## Suggest Questions

Get example questions that the semantic model can answer — useful for onboarding or seeding a UI:

```python
questions = analyst.suggest_questions(
    semantic_view="ANALYTICS.PUBLIC.SALES_VIEW",
    max_questions=5,
)
for q in questions:
    print(f"- {q}")
```

## Validate a Semantic Model

Check a semantic model or view for errors before running queries:

```python
result = analyst.validate_semantic_model(
    semantic_model_file="@analytics.public.models/sales_model.yaml"
)
print(result)
# or for a semantic view:
result = analyst.validate_semantic_model(
    semantic_view="ANALYTICS.PUBLIC.SALES_VIEW"
)
```

## Next Steps

- Explore [API Reference](../api/analyst.md) for detailed method documentation
- See [Examples](agents.md) for more code samples
- Learn about [Async Analyst](../api/async_analyst.md) for concurrent operations
- Read the [Cortex Agents Guide](agents.md) to understand how Agents and Analyst work together
