"""
Example: Async Cortex Agent Usage

Demonstrates async usage of Cortex Agents including:
- Creating agents asynchronously
- Running agents with streaming responses
- Managing threads
- Concurrent agent operations
"""

import asyncio

from cortex_agents import AsyncCortexAgent

# Configuration
DATABASE = "MY_DB"
SCHEMA = "MY_SCHEMA"


async def basic_async_agent():
    """Basic async agent usage"""
    print("=== Basic Async Agent Usage ===\n")

    async with AsyncCortexAgent() as agent:
        # Create an agent
        await agent.create_agent(
            name="REVENUE_AGENT",
            config={
                "comment": "Analyzes revenue data",
                "instructions": {
                    "system": "You are a helpful revenue analytics assistant.",
                    "response": "Provide clear, concise answers with data.",
                },
                "models": {"orchestration": "claude-sonnet-4-6"},
            },
            database=DATABASE,
            schema=SCHEMA,
        )
        print("✓ Agent created\n")

        # Run the agent
        response = await agent.run(
            "What was the total revenue last quarter?",
            agent_name="REVENUE_AGENT",
            database=DATABASE,
            schema=SCHEMA,
        )

        # Stream results
        print("Streaming response:")
        async for event in response:
            if event["type"] == "text.delta":
                print(event["data"]["text"], end="", flush=True)
            elif event["type"] == "status":
                print(f"\n[Status: {event['data']['message']}]")

        print("\n\n✓ Query completed\n")


async def concurrent_agents():
    """Run multiple agents concurrently"""
    print("=== Concurrent Agent Operations ===\n")

    async with AsyncCortexAgent() as agent:
        # Run multiple queries concurrently
        tasks = [
            agent.run("What's the total revenue?", agent_name="AGENT_1", database=DATABASE, schema=SCHEMA),
            agent.run("What's the customer count?", agent_name="AGENT_2", database=DATABASE, schema=SCHEMA),
            agent.run(
                "What's the average order value?",
                agent_name="AGENT_3",
                database=DATABASE,
                schema=SCHEMA,
            ),
        ]

        # Wait for all to complete
        responses = await asyncio.gather(*tasks)

        for i, response in enumerate(responses, 1):
            print(f"Agent {i} response:")
            # Iterate directly over response
            async for event in response:
                if event["type"] == "text.delta":
                    print(event["data"]["text"], end="", flush=True)
            print("\n")


async def async_thread_conversation():
    """Multi-turn conversation with threads (async)"""
    print("=== Async Thread Conversation ===\n")

    async with AsyncCortexAgent() as agent:
        # Create a conversation thread
        thread_id = (await agent.create_thread(origin_app="async_example"))["thread_id"]
        print(f"✓ Thread created: {thread_id}\n")

        # First message
        response1 = await agent.run(
            "What was our revenue in Q1?",
            agent_name="REVENUE_AGENT",
            database=DATABASE,
            schema=SCHEMA,
            thread_id=thread_id,
            parent_message_id=0,
        )

        print("User: What was our revenue in Q1?")
        print("Agent: ", end="")
        async for event in response1:
            if event["type"] == "text.delta":
                print(event["data"]["text"], end="", flush=True)
        print("\n")

        message_id = response1.message_id

        if message_id:
            # Follow-up question
            response2 = await agent.run(
                "How does that compare to Q2?",
                agent_name="REVENUE_AGENT",
                database=DATABASE,
                schema=SCHEMA,
                thread_id=thread_id,
                parent_message_id=message_id,
            )

            print("User: How does that compare to Q2?")
            print("Agent: ", end="")
            async for event in response2.astream():
                if event["type"] == "text.delta":
                    print(event["data"]["text"], end="", flush=True)
            print("\n")


async def async_feedback_example():
    """Submit feedback asynchronously"""
    print("=== Async Feedback Example ===\n")

    async with AsyncCortexAgent() as agent:
        # Run agent
        response = await agent.run(
            "Show me top customers",
            agent_name="REVENUE_AGENT",
            database=DATABASE,
            schema=SCHEMA,
        )

        # Collect response
        text_parts = []
        async for event in response.astream():
            if event["type"] == "text.delta":
                text_parts.append(event["data"]["text"])

        print("Response:", "".join(text_parts))

        # Submit positive feedback
        await agent.submit_feedback(
            agent_name="REVENUE_AGENT",
            database=DATABASE,
            schema=SCHEMA,
            positive=True,
            feedback_message="Excellent, clear response!",
            categories=["Something worked well"],
        )
        print("\n✓ Feedback submitted\n")


async def batch_agent_management():
    """Batch create and manage agents"""
    print("=== Batch Agent Management ===\n")

    async with AsyncCortexAgent() as agent:
        # Create multiple agents concurrently
        agent_configs = [
            ("SALES_AGENT", {"instructions": {"system": "Sales expert"}}),
            ("MARKETING_AGENT", {"instructions": {"system": "Marketing expert"}}),
            ("FINANCE_AGENT", {"instructions": {"system": "Finance expert"}}),
        ]

        create_tasks = [
            agent.create_agent(name, config, database=DATABASE, schema=SCHEMA) for name, config in agent_configs
        ]

        await asyncio.gather(*create_tasks)
        print("✓ All agents created\n")

        # List all agents
        agents = await agent.list_agents(database=DATABASE, schema=SCHEMA)
        print(f"Total agents: {len(agents)}")
        for a in agents:
            print(f"  - {a['name']}")
        print()


async def main():
    """Run all async examples"""
    examples = [
        ("Basic Usage", basic_async_agent),
        ("Concurrent Operations", concurrent_agents),
        ("Thread Conversations", async_thread_conversation),
        ("Feedback", async_feedback_example),
        ("Batch Management", batch_agent_management),
    ]

    for title, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"❌ Error in {title}: {e}\n")


if __name__ == "__main__":
    # Run all examples
    asyncio.run(main())
