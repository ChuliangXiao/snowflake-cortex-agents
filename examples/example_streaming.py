"""
Simple example of streaming with Cortex Agents.

This example shows:
1. How to use agent.run()
2. Direct iteration over responses
3. Real-time event processing

Requirements:
    uv sync
    Set SNOWFLAKE_ACCOUNT_URL and SNOWFLAKE_PAT environment variables

Usage:
    uv run python examples/example_streaming.py
"""

from cortex_agents import CortexAgent

# Database and schema configuration
DATABASE = "YOUR_DATABASE"
SCHEMA = "YOUR_SCHEMA"
AGENT_NAME = "YOUR_AGENT_NAME"
QUERY = "ASK YOUR QUERY HERE"


def example_streaming_with_context_manager():
    """Example: Direct iteration over agent responses.

    Agent responses are always SSE streams
    """
    print("=" * 60)
    print("Example 1: Direct Iteration (Recommended)")
    print("=" * 60)

    # Create agent - use 'with' for automatic cleanup
    with CortexAgent() as client:
        response = client.run(QUERY, agent_name=AGENT_NAME, database=DATABASE, schema=SCHEMA)

        # Iterate directly over response (no .stream() needed!)
        print("\n📊 Streaming events in real-time:\n")

        for event in response:
            event_type = event["type"]
            data = event["data"]

            # Print different event types
            if event_type == "text.delta":
                # Stream text as it arrives (don't print newline)
                print(data.get("text", ""), end="", flush=True)

            elif event_type == "thinking.delta":
                # Print thinking process
                print(f"\n💭 Thinking: {data.get('text', '')}")

            elif event_type == "tool_use":
                # Print when tools are called
                print(f"\n🔧 Using tool: {data.get('name', '')}")

            elif event_type == "tool_result":
                # Print tool results
                print("\n✅ Tool result received")

        print("\n\n" + "=" * 60)
        print("Streaming complete!")
        print("=" * 60)

    # Agent session is automatically closed here


def example_error_handling():
    """Example: Proper error handling with streaming.

    The 'with' statement ensures resources are cleaned up
    even if an error occurs during streaming.
    """
    print("\n" + "=" * 60)
    print("Example 2: Error Handling")
    print("=" * 60)

    try:
        with CortexAgent() as client:
            response = client.run(QUERY, agent_name=AGENT_NAME, database=DATABASE, schema=SCHEMA)

            # Iterate directly - errors are handled automatically
            for event in response:
                event_type = event["type"]

                if event_type == "error":
                    print(f"❌ Error: {event['data']}")
                    break

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        print("   (Resources cleaned up automatically by 'with' statement)")


def example_multiple_queries():
    """Example: Running multiple streaming queries efficiently.

    The agent session is reused across multiple queries.
    """
    print("\n" + "=" * 60)
    print("Example 3: Multiple Streaming Queries")
    print("=" * 60)

    queries = [
        "What is the total revenue?",
        "What is the count of patients?",
        "What is the monthly trend?",
    ]

    with CortexAgent() as client:
        for i, query in enumerate(queries, 1):
            print(f"\n📌 Query {i}: {query}")
            print("-" * 40)

            response = client.run(query, agent_name=AGENT_NAME, database=DATABASE, schema=SCHEMA)

            # Iterate directly over the response
            event_count = 0
            for _event in response:
                event_count += 1

            print(f"✅ Received {event_count} events")


if __name__ == "__main__":
    # Run all examples
    example_streaming_with_context_manager()
    example_error_handling()
    example_multiple_queries()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
