"""Cortex Analyst Response handling.

This module provides response wrappers for Cortex Analyst API responses,
including streaming support and convenient property access.

Inherits SSE parsing from :class:`BaseSSEResponse`.
"""

from copy import deepcopy
from typing import Any

from ._base_response import BaseSSEResponse


class AnalystResponse(BaseSSEResponse):
    """Wrapper for Cortex Analyst responses with convenient property access.

    Provides easy access to generated SQL statements, interpretation text,
    suggestions for ambiguous questions, confidence information, and streaming
    events.

    Examples:
        ```python
        response = analyst.message(
            "What is the revenue?",
            semantic_model_file="@stage/model.yaml"
        )

        # Stream events in real-time (response is directly iterable)
        for event in response:
            if event["type"] == "text.delta":
                print(event["data"]["text"], end="")

        # Or access final properties
        print(response.text)        # Interpretation
        print(response.sql)         # Generated SQL
        print(response.suggestions) # If ambiguous
        ```
    """

    def __init__(
        self,
        response: Any,
        stream: bool = True,
        is_async: bool = False,
        request_messages: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize the response wrapper.

        Args:
            response: Callable that returns httpx streaming context manager,
                or a dict for non-streaming responses.
            stream: Whether this is a streaming response. Defaults to True.
            is_async: Whether this is an async response. Defaults to False.
            request_messages: Original request messages for conversation continuity.
        """
        super().__init__(response, stream=stream, is_async=is_async)
        self._parsed_data: dict[str, Any] | None = None
        self._request_messages: list[dict[str, Any]] | None = (
            deepcopy(request_messages) if request_messages is not None else None
        )

    # ------------------------------------------------------------------
    # Override hooks from BaseSSEResponse
    # ------------------------------------------------------------------

    def _simplify_event(self, raw_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Map Analyst-specific SSE event types to simplified form."""
        if raw_type == "status":
            return {"type": "status", "data": {"status": data.get("status")}, "raw_type": raw_type}

        if raw_type == "message.content.delta":
            content_type = data.get("type")

            if content_type == "text":
                return {
                    "type": "text.delta",
                    "data": {"text": data.get("text_delta", ""), "index": data.get("index", 0)},
                    "raw_type": raw_type,
                }
            if content_type == "sql":
                return {
                    "type": "sql.delta",
                    "data": {
                        "sql": data.get("statement_delta", ""),
                        "index": data.get("index", 0),
                        "confidence": data.get("confidence"),
                    },
                    "raw_type": raw_type,
                }
            if content_type == "suggestions":
                sugg_delta = data.get("suggestions_delta", {})
                return {
                    "type": "suggestions.delta",
                    "data": {
                        "suggestion": sugg_delta.get("suggestion_delta", ""),
                        "suggestion_index": sugg_delta.get("index", 0),
                        "content_index": data.get("index", 0),
                    },
                    "raw_type": raw_type,
                }

        # Default: passthrough with raw_type preserved
        return {"type": raw_type, "data": data, "raw_type": raw_type}

    def _make_non_streaming_event(self, raw: Any) -> dict[str, Any]:
        return {"type": "message.completed", "data": raw, "raw_type": "message.completed"}

    # ------------------------------------------------------------------
    # Lazy parsed-data helpers (Analyst-specific)
    # ------------------------------------------------------------------

    def _parse_response(self) -> None:
        """Parse the response (lazy evaluation).

        Consumes streaming events if applicable and builds the final response
        data structure.
        """
        if self._parsed_data is not None:
            return

        if self._is_streaming:
            self._ensure_parsed()
            self._parsed_data = self._build_from_events()
        else:
            if isinstance(self._raw, dict):
                self._parsed_data = deepcopy(self._raw)
            else:
                raise TypeError("Expected dict response for non-streaming AnalystResponse")

        if self._parsed_data is not None and self._request_messages is not None:
            self._parsed_data.setdefault("request_messages", deepcopy(self._request_messages))

    def _get_parsed_data(self) -> dict[str, Any]:
        """Get parsed data after ensuring it's been parsed."""
        self._parse_response()
        assert self._parsed_data is not None
        return self._parsed_data

    def _build_from_events(self) -> dict:
        """Build complete response from collected streaming events.

        Reconstructs the full response by aggregating delta events and
        organizing content by type.
        """
        result: dict[str, Any] = {
            "message": {"role": "analyst", "content": []},
            "request_id": None,
            "warnings": [],
            "response_metadata": {},
        }

        if self._request_messages is not None:
            result["request_messages"] = deepcopy(self._request_messages)

        content_items: dict[int, dict[str, Any]] = {}

        for event in self._events:
            raw_type = event.get("raw_type", event.get("type"))
            # Use original parsed JSON data for building the response
            data = event.get("_raw_data", event.get("data", {}))

            if raw_type == "message.content.delta":
                idx = data.get("index", 0)
                content_type = data.get("type")

                if idx not in content_items:
                    content_items[idx] = {"type": content_type}

                if content_type == "text":
                    text_delta = data.get("text_delta", "")
                    content_items[idx]["text"] = content_items[idx].get("text", "") + text_delta

                elif content_type == "sql":
                    stmt_delta = data.get("statement_delta", "")
                    content_items[idx]["statement"] = content_items[idx].get("statement", "") + stmt_delta
                    if "confidence" in data:
                        content_items[idx]["confidence"] = data["confidence"]

                elif content_type == "suggestions":
                    if "suggestions" not in content_items[idx]:
                        content_items[idx]["suggestions"] = []
                    sugg_delta = data.get("suggestions_delta", {})
                    sugg_idx = sugg_delta.get("index", 0)
                    sugg_text = sugg_delta.get("suggestion_delta", "")
                    while len(content_items[idx]["suggestions"]) <= sugg_idx:
                        content_items[idx]["suggestions"].append("")
                    content_items[idx]["suggestions"][sugg_idx] += sugg_text

            elif raw_type == "status":
                if result.get("request_id") is None and "request_id" in data:
                    result["request_id"] = data["request_id"]

            elif raw_type == "warnings":
                result["warnings"] = data.get("warnings", [])

            elif raw_type == "response_metadata":
                result["response_metadata"] = data
                if result.get("request_id") is None and "request_id" in data:
                    result["request_id"] = data["request_id"]

            elif raw_type == "done":
                if result.get("request_id") is None and "request_id" in data:
                    result["request_id"] = data["request_id"]

        for idx in sorted(content_items.keys()):
            result["message"]["content"].append(content_items[idx])

        return result

    # ------------------------------------------------------------------
    # Convenience Properties
    # ------------------------------------------------------------------

    @property
    def text(self) -> str:
        """Get the interpretation text from the analyst."""
        parsed = self._get_parsed_data()
        content = parsed.get("message", {}).get("content", [])
        for item in content:
            if item.get("type") == "text":
                return item.get("text", "")
        return ""

    @property
    def sql(self) -> str | None:
        """Get the generated SQL statement (None if question was ambiguous)."""
        parsed = self._get_parsed_data()
        content = parsed.get("message", {}).get("content", [])
        for item in content:
            if item.get("type") == "sql":
                return item.get("statement")
        return None

    @property
    def suggestions(self) -> list[str]:
        """Get suggested questions (if question was ambiguous)."""
        parsed = self._get_parsed_data()
        content = parsed.get("message", {}).get("content", [])
        for item in content:
            if item.get("type") == "suggestions":
                return item.get("suggestions", [])
        return []

    @property
    def confidence(self) -> dict | None:
        """Get confidence information about the SQL generation."""
        parsed = self._get_parsed_data()
        content = parsed.get("message", {}).get("content", [])
        for item in content:
            if item.get("type") == "sql":
                return item.get("confidence")
        return None

    @property
    def verified_query_used(self) -> dict | None:
        """Get verified query information if one was used."""
        conf = self.confidence
        if conf:
            return conf.get("verified_query_used")
        return None

    @property
    def query_id(self) -> str | None:
        """Get the query ID from SQL execution."""
        parsed = self._get_parsed_data()
        metadata = parsed.get("response_metadata", {})
        if "query_id" in metadata:
            return metadata["query_id"]
        content = parsed.get("message", {}).get("content", [])
        for item in content:
            if item.get("type") == "sql" and "query_id" in item:
                return item["query_id"]
        return None

    @property
    def request_id(self) -> str | None:
        """Get the Snowflake request ID for this response.

        Checks HTTP response headers first (via BaseSSEResponse), then
        falls back to the parsed response data.
        """
        # Try base class (header-based)
        base_rid = super().request_id
        if base_rid:
            return base_rid
        # Fallback to parsed data
        parsed = self._get_parsed_data()
        return parsed.get("request_id")

    @property
    def warnings(self) -> list[dict]:
        """Get any warnings from the response."""
        parsed = self._get_parsed_data()
        return parsed.get("warnings", [])

    @property
    def response_metadata(self) -> dict:
        """Get response metadata (models used, question category, etc.)."""
        parsed = self._get_parsed_data()
        return parsed.get("response_metadata", {})

    @property
    def conversation_messages(self) -> list[dict[str, Any]]:
        """Get the full messages array for multi-turn conversations.

        Examples:
        ```python
        response1 = analyst.message("First question", ...)
        response2 = analyst.message(
            "Follow-up question",
            messages=response1.conversation_messages,
            ...
        )
        ```
        """
        parsed = self._get_parsed_data()
        history: list[dict[str, Any]] = []

        request_messages = parsed.get("request_messages")
        if isinstance(request_messages, list):
            history.extend(deepcopy(request_messages))
        elif self._request_messages is not None:
            history.extend(deepcopy(self._request_messages))

        analyst_message = parsed.get("message")
        if isinstance(analyst_message, dict):
            history.append(deepcopy(analyst_message))

        return history

    @property
    def sql_explanation(self) -> str | None:
        """Get Analyst's explanation of the generated SQL."""
        parsed = self._get_parsed_data()
        content = parsed.get("message", {}).get("content", [])
        for item in content:
            if item.get("type") == "sql" and "sql_explanation" in item:
                return item["sql_explanation"]
        return None

    @property
    def result_set(self) -> dict | None:
        """Get the SQL execution result set (if available)."""
        parsed = self._get_parsed_data()
        content = parsed.get("message", {}).get("content", [])
        for item in content:
            if item.get("type") == "sql" and "result_set" in item:
                return item["result_set"]
        return None

    @property
    def semantic_model_selection(self) -> str | None:
        """Get which semantic model was selected (when multiple provided)."""
        parsed = self._get_parsed_data()
        metadata = parsed.get("response_metadata", {})
        return metadata.get("semantic_model_selection")

    @property
    def cortex_search_retrieval(self) -> list[dict[str, Any]]:
        """Get Cortex Search retrieval results."""
        parsed = self._get_parsed_data()
        metadata = parsed.get("response_metadata", {})
        return metadata.get("cortex_search_retrieval", [])

    @property
    def is_semantic_sql(self) -> bool:
        """Check if generated SQL uses Semantic Views."""
        parsed = self._get_parsed_data()
        metadata = parsed.get("response_metadata", {})
        return metadata.get("is_semantic_sql", False)

    @property
    def analyst_latency_ms(self) -> float | None:
        """Get analyst processing latency in milliseconds."""
        parsed = self._get_parsed_data()
        metadata = parsed.get("response_metadata", {})
        return metadata.get("analyst_latency_ms")

    @property
    def question_category(self) -> str | None:
        """Get the question category determined by the analyst."""
        parsed = self._get_parsed_data()
        metadata = parsed.get("response_metadata", {})
        return metadata.get("question_category")

    @property
    def model_names(self) -> list[str]:
        """Get the names of LLM models used for processing."""
        parsed = self._get_parsed_data()
        metadata = parsed.get("response_metadata", {})
        return metadata.get("model_names", [])

    @property
    def analyst_orchestration_path(self) -> str | None:
        """Get the orchestration path taken during analysis."""
        parsed = self._get_parsed_data()
        metadata = parsed.get("response_metadata", {})
        return metadata.get("analyst_orchestration_path")
