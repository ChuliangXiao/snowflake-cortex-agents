"""Parser for Snowflake Cortex Agent run responses.
Based on: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-run#streaming-responses

Provides easy-to-use response wrapper and SSE event parsing.

Supports both:
- Snowflake SSEClient (from snowflake.core.rest)
- Standard httpx.Response objects with SSE streams (sync and async)
"""

from enum import Enum
from typing import Any

from .._base_response import BaseSSEResponse


class EventType(str, Enum):
    """Enumeration of SSE event types from agent:run endpoint.

    SSE (Server-Sent Events) events include various message types for streaming
    agent responses including text deltas, tool usage, metadata, and errors.
    """

    # Response events
    RESPONSE = "response"
    RESPONSE_TEXT = "response.text"
    RESPONSE_TEXT_DELTA = "response.text.delta"
    RESPONSE_TEXT_ANNOTATION = "response.text.annotation"
    RESPONSE_THINKING = "response.thinking"
    RESPONSE_THINKING_DELTA = "response.thinking.delta"
    RESPONSE_TOOL_USE = "response.tool_use"
    RESPONSE_TOOL_RESULT = "response.tool_result"
    RESPONSE_TOOL_RESULT_STATUS = "response.tool_result.status"
    RESPONSE_TOOL_RESULT_ANALYST_DELTA = "response.tool_result.analyst.delta"
    RESPONSE_TABLE = "response.table"
    RESPONSE_CHART = "response.chart"
    RESPONSE_STATUS = "response.status"
    RESPONSE_WARNING = "response.warning"
    RESPONSE_SUGGESTED_QUERIES = "response.suggested_queries"
    # Other events
    METADATA = "metadata"
    ERROR = "error"
    DONE = "done"
    EXECUTION_TRACE = "execution_trace"  # OpenTelemetry traces


class AgentResponse(BaseSSEResponse):
    """Wrapper for agent run response with easy access to results.

    Inherits SSE parsing, iteration, and request_id capture from
    :class:`BaseSSEResponse`.  Adds Agent-specific convenience properties
    for text, SQL, thinking, charts, tables, tools, etc.

    Examples:
        ```python
        with CortexAgent(...) as agent:
            response = agent.run(
                "What's the revenue?",
                agent_name="MY_AGENT",
                database="MY_DB",
                schema="MY_SCHEMA"
            )

            # Stream events in real-time (response is directly iterable)
            for event in response:
                if event["type"] == "text.delta":
                    print(event["data"]["text"], end="", flush=True)

        # Or just get final results
        print(response.text)        # Final text response
        print(response.sql)         # SQL query if any
        print(response.thinking)    # Agent reasoning
        print(response.query_id)    # Snowflake query ID

        # Get SQL execution results
        result_set = response.get_sql_result()
        if result_set:
            for row in result_set['data']:
                print(row)

        # Get structured data
        charts = response.get_charts()
        tables = response.get_tables()
        ```
    """

    def __init__(self, raw_response: Any, stream: bool = True, is_async: bool = False):
        """Initialize response wrapper.

        Args:
            raw_response: Callable that returns httpx streaming context manager,
                or a dict for non-streaming responses.
            stream: Whether response is streaming. Defaults to True.
            is_async: Whether this is an async response. Defaults to False.
        """
        super().__init__(raw_response, stream=stream, is_async=is_async)

    @property
    def text(self) -> str:
        """Get final text response (concatenated from all text events by content_index).

        Real SSE streams may emit multiple ``response.text`` events at different
        ``content_index`` values (e.g., answer, explanation, methodology).
        This property concatenates ALL text blocks in content_index order.

        Returns:
            str: Complete text response
        """
        self._ensure_parsed()

        # Collect text from all 'text' events, keyed by content_index
        text_by_index: dict[int, str] = {}
        for event in self._events:
            if event["type"] == "text":
                idx = event["data"].get("content_index", 0)
                text_by_index[idx] = event["data"].get("text", "")

        if text_by_index:
            return "".join(text_by_index[idx] for idx in sorted(text_by_index.keys()))

        # Fallback: concatenate text.delta events
        # Group by content_index to handle multiple text blocks
        delta_by_index: dict[int, list[str]] = {}
        for event in self._events:
            if event["type"] == "text.delta":
                content_index = event["data"].get("content_index", 0)
                text = event["data"].get("text", "")
                if content_index not in delta_by_index:
                    delta_by_index[content_index] = []
                delta_by_index[content_index].append(text)

        # Concatenate all text blocks in order
        all_text = []
        for idx in sorted(delta_by_index.keys()):
            all_text.append("".join(delta_by_index[idx]))

        return "".join(all_text)

    @property
    def thinking(self) -> str:
        """Get agent's reasoning/thinking tokens (concatenated from all thinking blocks).

        Returns:
            str: Complete thinking process
        """
        self._ensure_parsed()

        # First try to get the final 'thinking' events (complete thinking)
        thinking_texts = []
        for event in self._events:
            if event["type"] == "thinking":
                thinking_texts.append(event["data"].get("text", ""))

        if thinking_texts:
            return "\n".join(thinking_texts)

        # Fallback: concatenate thinking.delta events
        # Group by content_index to handle multiple thinking blocks
        thinking_by_index: dict[int, list[str]] = {}
        for event in self._events:
            if event["type"] == "thinking.delta":
                content_index = event["data"].get("content_index", 0)
                text = event["data"].get("text", "")
                if content_index not in thinking_by_index:
                    thinking_by_index[content_index] = []
                thinking_by_index[content_index].append(text)

        # Concatenate all thinking blocks in order
        all_thinking = []
        for idx in sorted(thinking_by_index.keys()):
            all_thinking.append("".join(thinking_by_index[idx]))

        return "\n".join(all_thinking)

    @property
    def sql(self) -> str | None:
        """Get SQL query from Cortex Analyst tool (if any).

        Returns:
            Optional[str]: SQL query or None
        """
        self._ensure_parsed()

        # Check tool_result events for SQL from Cortex Analyst
        for event in self._events:
            if event["type"] == "tool_result":
                data = event["data"]
                # Check if it's a cortex_analyst_text_to_sql tool
                if data.get("type") == "cortex_analyst_text_to_sql":
                    # SQL is in content[0]['json']['sql']
                    content = data.get("content", [])
                    if content and len(content) > 0:
                        json_data = content[0].get("json", {})
                        if "sql" in json_data:
                            return json_data["sql"]

        # Fallback: check tool_result.analyst.delta events (older format)
        for event in self._events:
            if event["type"] == "tool_result.analyst.delta":
                sql = event["data"].get("sql")
                if sql:
                    return sql

        # Also check the final 'response' event
        for event in reversed(self._events):
            if event["type"] == "response":
                content = event["data"].get("content", [])
                for item in content:
                    if item.get("type") == "tool_result":
                        tool_result = item.get("tool_result", {})
                        if tool_result.get("type") == "cortex_analyst_text_to_sql":
                            result_content = tool_result.get("content", [])
                            if result_content:
                                json_data = result_content[0].get("json", {})
                                if "sql" in json_data:
                                    return json_data["sql"]

        return None

    @property
    def sql_explanation(self) -> str | None:
        """Get SQL explanation from Cortex Analyst (if any).

        Returns:
            Optional[str]: SQL explanation or None
        """
        self._ensure_parsed()

        # Check tool_result events for text explanation
        for event in self._events:
            if event["type"] == "tool_result":
                data = event["data"]
                if data.get("type") == "cortex_analyst_text_to_sql":
                    content = data.get("content", [])
                    if content and len(content) > 0:
                        json_data = content[0].get("json", {})
                        if "text" in json_data:
                            return json_data["text"]

        # Fallback: check tool_result.analyst.delta events
        for event in self._events:
            if event["type"] == "tool_result.analyst.delta":
                explanation = event["data"].get("sql_explanation")
                if explanation:
                    return explanation

        return None

    @property
    def query_id(self) -> str | None:
        """Get Snowflake query ID from SQL execution (if any).

        Useful for tracking query execution in Snowflake.

        Returns:
            Optional[str]: Query ID or None
        """
        self._ensure_parsed()

        # Check tool_result events for query_id
        for event in self._events:
            if event["type"] == "tool_result":
                data = event["data"]
                if data.get("type") == "cortex_analyst_text_to_sql":
                    content = data.get("content", [])
                    if content and len(content) > 0:
                        json_data = content[0].get("json", {})
                        if "query_id" in json_data:
                            return json_data["query_id"]

        return None

    def get_sql_result(self) -> dict | None:
        """Get SQL execution result set from Cortex Analyst (if any).

        Returns the full result_set including data, metadata, and statementHandle.

        Returns:
            Optional[Dict]: Result set or None

        Examples:
        ```python
        result = response.get_sql_result()
        if result:
            data = result['data']  # Array of rows
            metadata = result['resultSetMetaData']
            print(f"Returned {metadata['numRows']} rows")
            for row in data:
                print(row)
        ```
        """
        self._ensure_parsed()

        # Check tool_result events for result_set
        for event in self._events:
            if event["type"] == "tool_result":
                data = event["data"]
                if data.get("type") == "cortex_analyst_text_to_sql":
                    content = data.get("content", [])
                    if content and len(content) > 0:
                        json_data = content[0].get("json", {})
                        if "result_set" in json_data:
                            return json_data["result_set"]

        return None

    def get_charts(self) -> list[dict]:
        """Get all chart specifications (Vega-Lite).

        Returns:
            list[Dict]: List of chart specs
        """
        self._ensure_parsed()
        charts = []
        for event in self._events:
            if event["type"] == "chart":
                charts.append(event["data"])
        return charts

    def get_tables(self) -> list[dict]:
        """Get all data tables.

        Returns:
            list[Dict]: List of tables with result_set data
        """
        self._ensure_parsed()
        tables = []
        for event in self._events:
            if event["type"] == "table":
                tables.append(event["data"])
        return tables

    def get_tool_uses(self) -> list[dict]:
        """Get all tool invocations.

        Returns:
            list[Dict]: List of tool use events
        """
        self._ensure_parsed()
        tools = []
        for event in self._events:
            if event["type"] == "tool_use":
                tools.append(event["data"])
        return tools

    def get_tool_results(self) -> list[dict]:
        """Get all tool execution results.

        Returns:
            list[Dict]: List of tool results
        """
        self._ensure_parsed()
        results = []
        for event in self._events:
            if event["type"] == "tool_result":
                results.append(event["data"])
        return results

    def get_metadata(self) -> list[dict]:
        """Get message metadata (includes message_id for follow-ups).

        Returns:
            list[dict]: List of metadata dicts with role and message_id
        """
        self._ensure_parsed()
        return [event["data"]["metadata"] for event in reversed(self._events) if event["type"] == "metadata"]

    @property
    def message_id(self) -> str | None:
        """Get the last assistant's message ID (for thread continuity).

        Returns:
            Message ID as provided by the API (typically an integer) or None if not available.
        """
        metadata = self.get_metadata()
        return metadata[0].get("message_id") if metadata else None

    def get_final_response(self) -> dict | None:
        """Get the final aggregated response event.

        Returns:
            Optional[Dict]: Complete response or None
        """
        self._ensure_parsed()
        for event in reversed(self._events):
            if event["raw_type"] == "response":
                return event["data"]
        return None

    @property
    def run_id(self) -> str | None:
        """Get the run ID from metadata events.

        The run_id is typically found in the metadata of the final response
        or in ``response.metadata`` events.

        Returns:
            Optional[str]: The run ID or None
        """
        self._ensure_parsed()

        # Check final aggregated response first
        for event in reversed(self._events):
            if event["raw_type"] == "response":
                metadata = event["data"].get("metadata", {})
                if isinstance(metadata, dict) and "run_id" in metadata:
                    return metadata["run_id"]

        # Check metadata events
        for event in self._events:
            if event["type"] == "metadata":
                rid = event["data"].get("run_id")
                if rid:
                    return rid

        return None

    def get_token_usage(self) -> dict | None:
        """Get token usage information from the response metadata.

        Returns:
            Optional[Dict]: Token usage dict (e.g. ``{"tokens_consumed": 1234}``) or None
        """
        self._ensure_parsed()

        # Check final aggregated response
        for event in reversed(self._events):
            if event["raw_type"] == "response":
                metadata = event["data"].get("metadata", {})
                if isinstance(metadata, dict) and "usage" in metadata:
                    return metadata["usage"]

        # Check metadata events
        for event in self._events:
            if event["type"] == "metadata":
                usage = event["data"].get("usage")
                if usage:
                    return usage

        return None

    def get_warnings(self) -> list[str]:
        """Get all warning messages from the response.

        Warnings are emitted as ``response.warning`` SSE events.

        Returns:
            list[str]: List of warning message strings
        """
        self._ensure_parsed()
        warnings = []
        for event in self._events:
            if event["raw_type"] in ("response.warning", "warning"):
                msg = event["data"].get("message") or event["data"].get("warning", "")
                if msg:
                    warnings.append(msg)
        return warnings

    def get_suggested_queries(self) -> list[str]:
        """Get suggested follow-up queries from the response.

        These are emitted as ``response.suggested_queries`` SSE events.

        Returns:
            list[str]: List of suggested query strings
        """
        self._ensure_parsed()
        queries: list[str] = []
        for event in self._events:
            if event["raw_type"] == "response.suggested_queries":
                data = event["data"]
                if isinstance(data, dict):
                    sq = data.get("suggested_queries", [])
                    if isinstance(sq, list):
                        queries.extend(sq)
                    elif isinstance(sq, str):
                        queries.append(sq)
        return queries

    def get_annotations(self) -> list[dict]:
        """Get all annotations from text events.

        Annotations (e.g., citations, references) may appear in
        ``response.text`` or ``response.text.annotation`` events.

        Returns:
            list[Dict]: List of annotation dicts
        """
        self._ensure_parsed()
        annotations: list[dict] = []
        for event in self._events:
            if event["raw_type"] == "response.text.annotation":
                annotations.append(event["data"])
            elif event["type"] == "text":
                ann = event["data"].get("annotations")
                if isinstance(ann, list):
                    annotations.extend(ann)
        return annotations

    @property
    def is_elicitation(self) -> bool:
        """Check if the response is an elicitation request (asking for more info).

        Returns:
            bool: True if any text event has ``is_elicitation`` set
        """
        self._ensure_parsed()
        for event in self._events:
            if event["type"] == "text" and event["data"].get("is_elicitation"):
                return True
        return False
