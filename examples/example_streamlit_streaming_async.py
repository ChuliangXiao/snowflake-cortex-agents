"""
Async Streaming Cortex Agents in Streamlit with Concurrent Tabs.

This app demonstrates:
1. Async streaming with AsyncCortexAgent
2. Multiple concurrent agent calls
3. Real-time updates in separate tabs
4. Dynamic tab creation for each query
5. Proper resource management with async context managers

Requirements:
    uv sync --extra charts
    uv pip install streamlit

Usage:
    uv run streamlit run examples/example_streamlit_streaming_async.py
"""

import asyncio
import json

import streamlit as st

from cortex_agents import AsyncCortexAgent
from cortex_agents.chart_utils import plot_charts

# Configuration
DATABASE = "YOUR_DATABASE"
SCHEMA = "YOUR_SCHEMA"
AGENT_NAME = "YOUR_AGENT_NAME"

# Session state keys
SESSIONS_KEY = "queries"  # Changed from "async_sessions"
CURRENT_TAB_KEY = "current_tab"
CALL_COUNTER_KEY = "call_counter"


def initialize_session_state():
    """Initialize Streamlit session state for async operations."""
    if SESSIONS_KEY not in st.session_state:
        st.session_state[SESSIONS_KEY] = []
    if CURRENT_TAB_KEY not in st.session_state:
        st.session_state[CURRENT_TAB_KEY] = 0
    if CALL_COUNTER_KEY not in st.session_state:
        st.session_state[CALL_COUNTER_KEY] = 0
    if SESSIONS_KEY not in st.session_state:
        st.session_state[SESSIONS_KEY] = []
    if CURRENT_TAB_KEY not in st.session_state:
        st.session_state[CURRENT_TAB_KEY] = 0
    if CALL_COUNTER_KEY not in st.session_state:
        st.session_state[CALL_COUNTER_KEY] = 0


async def stream_agent_response(
    query: str,
    thinking_placeholder,
    thinking_status,
    text_placeholder,
    sql_placeholder,
    event_debug_area,
) -> dict:
    """
    Stream agent response asynchronously.

    Args:
        query: User's question
        thinking_placeholder: Streamlit placeholder for thinking expander content
        thinking_status: Streamlit placeholder for thinking status
        text_placeholder: Streamlit placeholder for response text
        sql_placeholder: Streamlit placeholder for SQL code
        event_debug_area: Streamlit placeholder for event type debug info

    Returns:
        Dict: Summary of the streamed response
    """
    try:
        # Initialize buffers
        text_buffer = []
        thinking_buffer = []
        sql_buffer = []
        all_events = []
        event_type_counts: dict[str, int] = {}

        async with AsyncCortexAgent() as agent:
            # Run agent with streaming
            response = await agent.run(query, agent_name=AGENT_NAME, database=DATABASE, schema=SCHEMA)

            # Stream events asynchronously using direct iteration
            async for event in response:
                all_events.append(event)
                event_type = event["type"]
                data = event["data"]

                # Track event types for debugging
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

                # Update text column as it arrives
                if event_type == "text.delta":
                    text = data.get("text", "")
                    text_buffer.append(text)
                    text_placeholder.write("".join(text_buffer))

                # Update thinking column as it arrives
                elif event_type == "thinking.delta":
                    thinking = data.get("text", "")
                    thinking_buffer.append(thinking)
                    thinking_placeholder.write("".join(thinking_buffer))
                    thinking_status.caption("💭 Thinking...")

                # Extract SQL from tool_result events
                elif event_type == "tool_result":
                    tool_type = data.get("type", "")
                    if tool_type == "cortex_analyst_text_to_sql":
                        content = data.get("content", [])
                        if content and len(content) > 0:
                            json_data = content[0].get("json", {})
                            sql = json_data.get("sql", "")
                            if sql:
                                sql_buffer.append(sql)
                                sql_placeholder.code("".join(sql_buffer), language="sql")

            # Clear thinking status
            thinking_status.caption("✅ Done thinking")

            # Debug: Show all event types received
            event_debug_area.json(event_type_counts)

            # Get final response data
            charts = response.get_charts()

            return {
                "success": True,
                "events": len(all_events),
                "event_types": event_type_counts,
                "has_charts": len(charts) > 0,
                "text": "".join(text_buffer),
                "thinking": "".join(thinking_buffer),
                "sql": "".join(sql_buffer),
                "charts": charts,
                "error": None,
            }

    except Exception as e:
        event_debug_area.error(f"❌ Error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "events": 0,
            "event_types": {},
            "has_charts": False,
            "text": "",
            "thinking": "",
            "sql": "",
            "charts": [],
        }


async def run_and_render_query(
    query_text: str,
    thinking_placeholder,
    thinking_status,
    text_placeholder,
    sql_placeholder,
    event_debug_area,
    final_result_placeholder,
) -> dict:
    """Run a single query, stream results, and render final output."""
    result = await stream_agent_response(
        query_text,
        thinking_placeholder,
        thinking_status,
        text_placeholder,
        sql_placeholder,
        event_debug_area,
    )

    # Render the final results in the provided placeholder
    with final_result_placeholder:
        st.divider()
        if result["success"]:
            st.success(f"✅ Stream complete! ({result['events']} events, {len(result['charts'])} chart(s))")
            if result["charts"]:
                st.subheader("📊 Charts")
                try:
                    chart_objects = plot_charts(result["charts"], interactive=True)
                    for chart in chart_objects:
                        st.vega_lite_chart(json.loads(chart.to_json()), use_container_width=True)
                except Exception as e:
                    st.error(f"Error plotting charts: {str(e)}")
            else:
                st.info("No charts generated in this response")
        else:
            st.error(f"❌ Query failed: {result['error']}")

    return result


async def display_and_run_queries():
    """
    Display tabs for each query in session_state and run them concurrently.
    This function is designed to be called on every Streamlit rerun.
    """
    queries = st.session_state.get(SESSIONS_KEY, [])
    if not queries:
        st.info("Submit a query to begin.")
        return

    # Create placeholder containers for each query
    tabs = st.tabs([f"Query {i + 1}" for i in range(len(queries))])
    tasks = []

    for tab, query_text in zip(tabs, queries, strict=True):
        with tab:
            st.write(f"**Query:** {query_text}")
            st.divider()

            # Set up the layout from the other app
            with st.expander("🧠 Thinking Process", expanded=True):
                thinking_placeholder = st.empty()
                thinking_status = st.empty()

            col_text, col_sql = st.columns([2, 1])
            with col_text:
                st.subheader("📝 Response")
                text_placeholder = st.empty()
            with col_sql:
                st.subheader("💾 SQL")
                sql_placeholder = st.empty()

            with st.expander("📊 Event Types Debug"):
                event_debug_area = st.empty()

            # Add a placeholder for the final results
            final_result_placeholder = st.empty()

            # Create an async task for the agent call and rendering
            task = run_and_render_query(
                query_text,
                thinking_placeholder,
                thinking_status,
                text_placeholder,
                sql_placeholder,
                event_debug_area,
                final_result_placeholder,
            )
            tasks.append(task)

    # Run all tasks concurrently
    results = await asyncio.gather(*tasks)

    # Process and display final results (charts, summaries) after all streams complete
    render_summary(results)


def render_summary(results: list[dict]):
    """Render a summary of all query results."""
    st.divider()
    st.subheader("📊 Overall Summary")

    cols = st.columns(len(results))

    for i, (col, result) in enumerate(zip(cols, results, strict=True)):
        with col:
            if result["success"]:
                st.metric(f"Query {i + 1}", "✅ Success")
                st.caption(f"Events: {result['events']}")
                st.caption(f"Unique types: {len(result['event_types'])}")
            else:
                st.metric(f"Query {i + 1}", "❌ Failed")
                st.caption(f"Error: {result['error'][:30]}...")


def main():
    """Main Streamlit app."""
    st.set_page_config(page_title="Async Cortex Agent - Interactive", layout="wide")

    st.title("🚀 Async Cortex Agent - Interactive Queries")

    initialize_session_state()

    # Sidebar controls
    with st.sidebar:
        st.subheader("⚙️ Configuration")
        st.write(f"**Database:** {DATABASE}")
        st.write(f"**Schema:** {SCHEMA}")
        st.write(f"**Agent:** {AGENT_NAME}")
        st.divider()
        st.markdown("""
        This app demonstrates an interactive, async streaming workflow.

        - **Submit Queries**: Type a query in the main input and hit enter.
        - **Add More Queries**: Submit new queries while others are running.
        - **Concurrent Execution**: All submitted queries run in parallel.
        - **Real-time Tabs**: Each query gets its own tab with live updates.
        """)
        if st.button("Clear All Queries"):
            st.session_state[SESSIONS_KEY] = []
            st.rerun()

    # Main area for query input and results
    with st.form(key="query_form"):
        query_input = st.text_area(
            "Enter your query:",
            placeholder="e.g., What is the monthly revenue this year?",
            key="query_input_main",
        )
        submitted = st.form_submit_button("Submit")

    if submitted and query_input:
        st.session_state[SESSIONS_KEY].append(query_input)
        st.rerun()

    # Display and run all queries in the session state
    try:
        asyncio.run(display_and_run_queries())
    except Exception as e:
        st.error(f"An error occurred: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
