"""
Streaming in Streamlit with Cortex Agents.

Demonstrates how to stream agent responses in real-time within Streamlit.
Perfect for displaying text, charts, and thinking simultaneously.

Requirements:
    uv sync --extra charts
    uv pip install streamlit

Usage:
    uv run streamlit run examples/example_streamlit_streaming.py
"""

import json

import streamlit as st

from cortex_agents import CortexAgent
from cortex_agents.chart_utils import plot_charts

DATABASE = "YOUR_DATABASE"
SCHEMA = "YOUR_SCHEMA"
AGENT_NAME = "YOUR_AGENT_NAME"
QUERY = "ASK YOUR QUERY HERE"


# Configure Streamlit
st.set_page_config(page_title="Cortex Agent Streaming", layout="wide")
st.title("🤖 Cortex Agent - Concurrent Streaming Demo")

# Initialize session state for caching streamed events
if "streamed_events" not in st.session_state:
    st.session_state.streamed_events = None
if "last_run_summary" not in st.session_state:
    st.session_state.last_run_summary = None


def demo_blocking_approach(query: str):
    """Traditional approach: blocking property access (blocks UI updates)."""
    st.subheader("❌ Traditional Blocking Approach")
    st.write("""
    This approach uses `.text`, `.thinking`, `.get_charts()` properties.
    **Problem**: UI is blocked until entire stream is consumed.
    """)

    if st.button("Run Agent (Blocking)", key="blocking"):
        client = CortexAgent()

        with st.spinner("Running agent..."):
            response = client.run(query, agent_name=AGENT_NAME, database=DATABASE, schema=SCHEMA)

        # All of these block until stream is fully consumed
        st.subheader("Agent Thinking")
        st.write(response.thinking)

        st.subheader("Response")
        st.write(response.text)

        st.subheader("Charts")
        for chart in response.get_charts():
            st.json(chart)


def demo_concurrent_approach(query: str):
    """Streamlit-native approach: real-time streaming with placeholders."""
    st.subheader("✅ Streamlit Native Approach (Recommended)")
    run_agent = st.button("🔄 Run Agent (Streaming)", key="streaming")

    if run_agent:
        # Set up thinking expander at the top
        with st.expander("🧠 Thinking Process", expanded=True):
            thinking_placeholder = st.empty()
            thinking_status = st.empty()

        # Set up columns for text (2 width) and SQL (1 width)
        col_text, col_sql = st.columns([2, 1])

        with col_text:
            st.subheader("📝 Response")
            text_placeholder = st.empty()

        with col_sql:
            st.subheader("💾 SQL")
            sql_placeholder = st.empty()

        # Buffers to accumulate stream data
        text_buffer = []
        thinking_buffer = []
        sql_buffer = []
        all_events = []  # Cache all events for dev iteration

        # Stream events and update UI in real-time
        with st.spinner("Streaming response..."):
            with CortexAgent() as client:
                response = client.run(query, agent_name=AGENT_NAME, database=DATABASE, schema=SCHEMA)

                event_type_counts: dict[str, int] = {}
                for event in response:
                    all_events.append(event)  # Cache event
                    event_type = event["type"]
                    data = event["data"]

                    # Track event types for debugging
                    event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

                    # Update text column as it arrives
                    if event_type == "text.delta":
                        text_buffer.append(data.get("text", ""))
                        text_placeholder.write("".join(text_buffer))

                    # Update thinking column as it arrives
                    elif event_type == "thinking.delta":
                        thinking_buffer.append(data.get("text", ""))
                        thinking_placeholder.write("".join(thinking_buffer))
                        thinking_status.caption("💭 Thinking...")

                    # Extract SQL from tool_result events (cortex_analyst_text_to_sql tool)
                    elif event_type == "tool_result":
                        tool_type = data.get("type", "")
                        if tool_type == "cortex_analyst_text_to_sql":
                            # SQL is nested in content[0]['json']['sql']
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
            st.session_state.event_type_counts = event_type_counts

        # Get properly formatted charts from response (only after stream is consumed)
        charts = response.get_charts()

        # Store in session state for dev iteration and persistence
        st.session_state.streamed_events = all_events
        st.session_state.last_run_summary = {
            "text": "".join(text_buffer),
            "thinking": "".join(thinking_buffer),
            "sql": "".join(sql_buffer),
            "charts": charts,
            "event_count": len(all_events),
            "event_types": list({e["type"] for e in all_events}),
        }

        # Show completion summary
        st.success(f"✅ Stream complete! ({len(all_events)} events, {len(charts)} chart(s))")

        # Debug: Show event types received
        with st.expander("📊 Event Types Debug"):
            st.write("**Event types received during stream:**")
            st.json(st.session_state.event_type_counts)
            st.write(f"**Total unique event types:** {len(st.session_state.event_type_counts)}")
            if not charts:
                st.warning("⚠️ No charts in response")

        # Plot charts
        st.subheader("📊 Charts")
        if charts:
            try:
                chart_objects = plot_charts(charts, interactive=True)
                for chart in chart_objects:
                    st.vega_lite_chart(json.loads(chart.to_json()), width="stretch")
            except Exception as e:
                st.error(f"Error plotting charts: {str(e)}")
                import traceback

                traceback.print_exc()
        else:
            st.info("No charts generated in this response")


def main():
    """Main app with tabs for different approaches."""
    query = st.text_input(f"Ask question about Agent **{AGENT_NAME}**", key="query_input")
    if query:
        # Create tabs for different approaches
        tab1, tab2 = st.tabs(
            [
                "Streaming (Recommended)",
                "Blocking (Old Way)",
            ]
        )

        with tab1:
            demo_concurrent_approach(query)

        with tab2:
            demo_blocking_approach(query)


if __name__ == "__main__":
    main()
