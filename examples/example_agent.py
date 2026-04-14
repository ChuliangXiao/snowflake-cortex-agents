"""
Simple example demonstrating the Cortex Agents SDK.
"""

from cortex_agents import CortexAgent


def main():
    # Initialize with credentials (or use environment variables)
    # If not provided, reads from SNOWFLAKE_ACCOUNT_URL and SNOWFLAKE_PAT env vars
    agent = CortexAgent()

    # Define your database and schema
    DATABASE = "YOUR_DATABASE"
    SCHEMA = "YOUR_SCHEMA"

    print("=" * 60)
    print("Example 1: Create and run a simple agent")
    print("=" * 60)

    # Create a simple agent
    agent.create_agent(
        name="DEMO_AGENT",
        config={
            "instructions": {
                "system": "You are a helpful data analyst assistant.",
                "profile": "Provide clear, concise answers with supporting data.",
            },
            "models": {"orchestration": "claude-sonnet-4-6"},
            "tools": [{"type": "builtin_function", "name": "QUERY_WAREHOUSE"}],
        },
        database=DATABASE,
        schema=SCHEMA,
    )
    print("✓ Agent 'DEMO_AGENT' created")

    # Run a simple query
    print("\nRunning query: 'What tables are available?'")
    response = agent.run(
        "What tables are available in this schema?",
        agent_name="DEMO_AGENT",
        database=DATABASE,
        schema=SCHEMA,
    )

    # Stream the response
    print("\nStreaming response:")
    print("-" * 60)
    for event in response:
        if event["type"] == "text.delta":
            print(event["data"]["text"], end="", flush=True)
    print("\n" + "-" * 60)

    # Access final results
    print("\nFinal results:")
    print(f"Text: {response.text[:200]}..." if len(response.text) > 200 else f"Text: {response.text}")
    if response.sql:
        print(f"SQL used: {response.sql}")

    print("\n" + "=" * 60)
    print("Example 2: Thread-based conversation")
    print("=" * 60)

    # Create a conversation thread with origin_app (max 16 bytes)
    thread_id = agent.create_thread(origin_app="example_agent")["thread_id"]
    print(f"✓ Thread created: {thread_id}")

    # Have a multi-turn conversation
    queries = [
        "List the first 3 tables in this schema",
        "Tell me more about the first table you mentioned",
    ]

    parent_id = 0

    for i, query in enumerate(queries, 1):
        print(f"\nQuery {i}: {query}")
        response = agent.run(
            query,
            agent_name="DEMO_AGENT",
            database=DATABASE,
            schema=SCHEMA,
            thread_id=thread_id,
            parent_message_id=parent_id,
        )

        print(f"Response: {response.text[:150]}..." if len(response.text) > 150 else f"Response: {response.text}")

        if response.message_id is not None:
            parent_id = response.message_id

    # Get thread history
    thread = agent.get_thread(thread_id)
    print(f"\n✓ Thread has {len(thread['messages'])} messages")

    # Cleanup
    agent.delete_thread(thread_id)
    print(f"✓ Thread {thread_id} deleted")

    print("\n" + "=" * 60)
    print("Example 3: One-off query without named agent")
    print("=" * 60)

    response = agent.run(
        "What is 25 * 4?",
        instructions={"system": "You are a helpful calculator."},
        models={"orchestration": "claude-sonnet-4-6"},
    )

    print(f"Response: {response.text}")

    print("\n" + "=" * 60)
    print("Example 4: Working with response components")
    print("=" * 60)

    response = agent.run("Show me some data about tables", agent_name="DEMO_AGENT", database=DATABASE, schema=SCHEMA)

    # Check for different response components
    charts = response.get_charts()
    tables = response.get_tables()
    tool_uses = response.get_tool_uses()

    print("Response components:")
    print(f"  - Charts: {len(charts)}")
    print(f"  - Tables: {len(tables)}")
    print(f"  - Tool uses: {len(tool_uses)}")
    print(f"  - Text length: {len(response.text)} characters")
    print(f"  - SQL queries: {1 if response.sql else 0}")

    # Get metadata
    metadata = response.get_metadata()
    if metadata:
        print("\nRequest metadata:")
        for key, value in metadata.items():
            print(f"  - {key}: {value}")

    print("\n" + "=" * 60)
    print("Example 5: Submit feedback")
    print("=" * 60)

    # Run a query and submit positive feedback
    response = agent.run("What is 10 + 15?", agent_name="DEMO_AGENT", database=DATABASE, schema=SCHEMA)
    print(f"Response: {response.text}")

    # Submit request-level feedback
    agent.submit_feedback(
        agent_name="DEMO_AGENT",
        database=DATABASE,
        schema=SCHEMA,
        positive=True,
        orig_request_id=response.request_id,
        feedback_message="Correct answer!",
        categories=["Something worked well", "Accurate"],
    )
    print("✓ Positive feedback submitted for specific response")

    # Submit agent-level feedback
    agent.submit_feedback(
        agent_name="DEMO_AGENT",
        database=DATABASE,
        schema=SCHEMA,
        positive=True,
        feedback_message="Overall a great agent!",
        categories=["Something worked well"],
    )
    print("✓ General feedback submitted for agent")

    print("\n" + "=" * 60)
    print("Cleanup")
    print("=" * 60)

    # Delete the demo agent
    agent.delete_agent("DEMO_AGENT", database=DATABASE, schema=SCHEMA)
    print("✓ Agent 'DEMO_AGENT' deleted")

    print("\n✅ All examples completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
