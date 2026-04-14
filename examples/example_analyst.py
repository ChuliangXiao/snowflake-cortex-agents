"""Simple example demonstrating Cortex Analyst for SQL generation."""

from cortex_agents import CortexAnalyst


def main():
    # Initialize Cortex Analyst
    analyst = CortexAnalyst()

    print("=" * 60)
    print("Example 1: Basic SQL generation with semantic model")
    print("=" * 60)

    # Generate SQL from natural language
    response = analyst.message(
        question="Which company had the most revenue?",
        semantic_model_file="@my_db.my_schema.my_stage/revenue_model.yaml",
    )

    print(f"\nInterpretation: {response.text}")
    print(f"\nGenerated SQL:\n{response.sql}")

    if response.confidence:
        print(f"\nConfidence info: {response.confidence}")

    print("\n" + "=" * 60)
    print("Example 2: Streaming response")
    print("=" * 60)

    response = analyst.message(
        question="Show top 10 customers by revenue",
        semantic_view="MY_DB.MY_SCHEMA.MY_SEMANTIC_VIEW",
    )

    print("\nStreaming interpretation:")
    for event in response:
        if event["type"] == "status":
            print(f"[Status: {event['data']['status']}]")
        elif event["type"] == "text.delta":
            print(event["data"]["text"], end="", flush=True)
        elif event["type"] == "sql.delta":
            print(f"\n\nSQL: {event['data']['sql']}")

    print("\n" + "=" * 60)
    print("Example 3: Using semantic view")
    print("=" * 60)

    response = analyst.message(
        question="What's the trend in sales over the last quarter?",
        semantic_view="MY_DB.MY_SCHEMA.SALES_VIEW",
    )

    print(f"Interpretation: {response.text}")
    print(f"SQL: {response.sql}")

    print("\n" + "=" * 60)
    print("Example 4: Multi-model selection")
    print("=" * 60)

    # Analyst will choose the most appropriate model
    response = analyst.message(
        question="Analyze customer behavior",
        semantic_models=[
            {"semantic_view": "MY_DB.MY_SCHEMA.CUSTOMER_VIEW"},
            {"semantic_view": "MY_DB.MY_SCHEMA.SALES_VIEW"},
            {"semantic_model_file": "@stage/product_model.yaml"},
        ],
    )

    print(f"Interpretation: {response.text}")
    print(f"SQL: {response.sql}")

    # Check which model was selected
    metadata = response.response_metadata
    if "semantic_model_selection" in metadata:
        print(f"\nSelected model: {metadata['semantic_model_selection']}")

    print("\n" + "=" * 60)
    print("Example 5: Handling ambiguous questions")
    print("=" * 60)

    response = analyst.message(
        question="revenue",  # Ambiguous question
        semantic_model_file="@stage/model.yaml",
    )

    if response.suggestions:
        print("Your question was ambiguous. Here are some suggestions:")
        for i, suggestion in enumerate(response.suggestions, 1):
            print(f"  {i}. {suggestion}")
    else:
        print(f"Interpretation: {response.text}")
        print(f"SQL: {response.sql}")

    print("\n" + "=" * 60)
    print("Example 6: Multi-turn conversation")
    print("=" * 60)

    # First question
    response1 = analyst.message(question="What's the total revenue?", semantic_view="MY_DB.MY_SCHEMA.MY_SEMANTIC_VIEW")
    print("Q1: What's the total revenue?")
    print(f"A1: {response1.text}")
    print(f"SQL1: {response1.sql}")

    # Follow-up question (maintains context)
    response2 = analyst.message(
        question="How does that compare to last year?",
        semantic_view="MY_DB.MY_SCHEMA.MY_SEMANTIC_VIEW",
        messages=response1.conversation_messages,  # Pass conversation history
    )
    print("\nQ2: How does that compare to last year?")
    print(f"A2: {response2.text}")
    print(f"SQL2: {response2.sql}")

    print("\n" + "=" * 60)
    print("Example 7: Submit feedback")
    print("=" * 60)

    response = analyst.message(question="Show Q1 revenue", semantic_view="MY_DB.MY_SCHEMA.MY_SEMANTIC_VIEW")

    print(f"SQL: {response.sql}")

    # Submit positive feedback
    analyst.submit_feedback(request_id=response.request_id, positive=True, feedback_message="Perfect SQL generation!")
    print("✓ Feedback submitted")

    print("\n" + "=" * 60)
    print("Example 8: Checking warnings")
    print("=" * 60)

    response = analyst.message(question="Analyze all data", semantic_view="MY_DB.MY_SCHEMA.MY_SEMANTIC_VIEW")

    if response.warnings:
        print("Warnings:")
        for warning in response.warnings:
            print(f"  - {warning.get('message')}")

    print("\n✅ All examples completed!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
