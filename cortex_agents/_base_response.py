"""Base SSE response parsing shared by Agent and Analyst response classes.

Provides the core SSE line-parsing state machine, sync/async iteration,
lazy evaluation helpers, and request_id extraction — all in one place.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Generator
from typing import Any


class BaseSSEResponse:
    """Base class for streaming SSE responses from Snowflake Cortex APIs.

    Handles:
    - SSE line parsing (``event:`` / ``data:`` / blank-line framing)
    - ``[DONE]`` sentinel detection
    - Event accumulation and lazy parsing
    - Sync and async iteration protocols
    - ``request_id`` capture from response headers

    Subclasses override :meth:`_simplify_event` to customise the yielded
    event dict shape and :meth:`_capture_request_id` if their header
    extraction differs.
    """

    def __init__(
        self,
        raw_response: Any,
        *,
        stream: bool = True,
        is_async: bool = False,
    ) -> None:
        self._raw = raw_response
        self._is_streaming = stream
        self._is_async = is_async
        self._events: list[dict[str, Any]] = []
        self._parsed = False
        self._request_id: str | None = None
        self._sync_stream_iter: Generator[dict[str, Any], None, None] | None = None
        self._async_stream_iter: AsyncGenerator[dict[str, Any], None] | None = None

    # ------------------------------------------------------------------
    # Iteration protocols
    # ------------------------------------------------------------------

    def __iter__(self) -> Generator[dict[str, Any], None, None]:
        return self._stream_events()

    def __aiter__(self) -> AsyncGenerator[dict[str, Any], None]:
        return self._astream_events()

    def stream(self) -> Generator[dict[str, Any], None, None]:
        """Backward-compatible alias for ``iter(self)``."""
        return self._stream_events()

    async def astream(self) -> AsyncGenerator[dict[str, Any], None]:
        """Backward-compatible alias for ``async for … in self``."""
        async for event in self._astream_events():
            yield event

    # ------------------------------------------------------------------
    # Sync SSE parser
    # ------------------------------------------------------------------

    def _stream_events(self) -> Generator[dict[str, Any], None, None]:
        if self._is_async and not self._parsed:
            raise RuntimeError("Async streaming responses must be consumed with 'async for' before synchronous access")

        if not self._is_streaming:
            yield from self._replay_non_streaming_event()
            return

        index = 0
        while True:
            while index < len(self._events):
                yield self._events[index]
                index += 1

            if self._parsed:
                return

            if self._sync_stream_iter is None:
                self._sync_stream_iter = self._open_sync_stream()

            try:
                event = next(self._sync_stream_iter)
            except StopIteration:
                self._parsed = True
                self._sync_stream_iter = None
                return

            yield event
            index += 1

    def _parse_sse_lines(self, lines: Any) -> Generator[dict[str, Any], None, None]:
        """Parse SSE framing from an iterable of text lines."""
        event_type: str | None = None
        data_lines: list[str] = []

        for line in lines:
            if not line:
                if event_type and data_lines:
                    yield from self._flush_event(event_type, data_lines)
                    event_type = None
                    data_lines = []
            elif line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())

        # Flush any remaining event at end-of-stream
        if event_type and data_lines:
            yield from self._flush_event(event_type, data_lines)

    # ------------------------------------------------------------------
    # Async SSE parser
    # ------------------------------------------------------------------

    async def _astream_events(self) -> AsyncGenerator[dict[str, Any], None]:
        if not self._is_async:
            for event in self._stream_events():
                yield event
            return

        if not self._is_streaming:
            for event in self._replay_non_streaming_event():
                yield event
            return

        index = 0
        while True:
            while index < len(self._events):
                yield self._events[index]
                index += 1

            if self._parsed:
                return

            if self._async_stream_iter is None:
                self._async_stream_iter = self._open_async_stream()

            try:
                event = await self._async_stream_iter.__anext__()
            except StopAsyncIteration:
                self._parsed = True
                self._async_stream_iter = None
                return

            yield event
            index += 1

    async def _aparse_sse_lines(self, lines: Any) -> AsyncGenerator[dict[str, Any], None]:
        """Parse SSE framing from an async iterable of text lines."""
        event_type: str | None = None
        data_lines: list[str] = []

        async for line in lines:
            if not line:
                if event_type and data_lines:
                    for ev in self._flush_event(event_type, data_lines):
                        yield ev
                    event_type = None
                    data_lines = []
            elif line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())

        # Flush any remaining event at end-of-stream
        if event_type and data_lines:
            for ev in self._flush_event(event_type, data_lines):
                yield ev

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _flush_event(self, event_type: str, data_lines: list[str]) -> Generator[dict[str, Any], None, None]:
        """Decode one SSE event and yield the simplified dict."""
        data_str = "\n".join(data_lines)

        # [DONE] sentinel — not valid JSON
        if data_str.strip() == "[DONE]":
            done_event: dict[str, Any] = {"type": "done", "data": {}, "raw_type": "done"}
            self._events.append(done_event)
            yield done_event
            return

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            error_event: dict[str, Any] = {
                "type": "error",
                "data": {"message": "Failed to parse event", "raw": data_str},
                "raw_type": event_type,
            }
            self._events.append(error_event)
            yield error_event
            return

        event = self._simplify_event(event_type, data)
        # Preserve original raw data for subclass post-processing
        event["_raw_data"] = data
        self._events.append(event)
        yield event

    def _open_sync_stream(self) -> Generator[dict[str, Any], None, None]:
        """Open the underlying sync stream exactly once and yield parsed events."""
        with self._raw() as response:
            response.raise_for_status()
            self._capture_request_id(response)
            yield from self._parse_sse_lines(response.iter_lines())

        self._parsed = True

    async def _open_async_stream(self) -> AsyncGenerator[dict[str, Any], None]:
        """Open the underlying async stream exactly once and yield parsed events."""
        async with self._raw() as response:
            response.raise_for_status()
            self._capture_request_id(response)
            async for event in self._aparse_sse_lines(response.aiter_lines()):
                yield event

        self._parsed = True

    def _replay_non_streaming_event(self) -> Generator[dict[str, Any], None, None]:
        """Replay or lazily materialize the single non-streaming event."""
        if not self._parsed:
            event = self._make_non_streaming_event(self._raw)
            self._events.append(event)
            self._parsed = True

        yield from self._events

    def _simplify_event(self, raw_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Build the dict yielded to callers.  Override in subclasses."""
        simple_type = raw_type.replace("response.", "") if raw_type.startswith("response.") else raw_type
        return {"type": simple_type, "data": data, "raw_type": raw_type}

    def _make_non_streaming_event(self, raw: Any) -> dict[str, Any]:
        """Build a single event dict for non-streaming responses."""
        return {"type": "response", "data": raw, "raw_type": "response"}

    def _capture_request_id(self, response: Any) -> None:
        """Extract Snowflake request-id from HTTP response headers."""
        headers = getattr(response, "headers", {})
        self._request_id = (
            headers.get("x-snowflake-request-id") or headers.get("x-request-id") or headers.get("request-id")
        )

    # ------------------------------------------------------------------
    # Lazy-parse helpers
    # ------------------------------------------------------------------

    def _ensure_parsed(self) -> None:
        """Consume the stream if not already done."""
        if self._is_async and not self._parsed:
            raise RuntimeError(
                "Async streaming responses must be fully consumed asynchronously before synchronous access"
            )

        if not self._parsed:
            for _ in self:
                pass

    @property
    def request_id(self) -> str | None:
        """Snowflake request ID captured from response headers or event data."""
        if self._request_id:
            return self._request_id

        # Trigger at least one event to capture from headers
        if not self._parsed and self._is_streaming:
            try:
                for _ in self:
                    break
            except StopIteration:
                pass

        if self._request_id:
            return self._request_id

        # Fallback: search event payloads
        self._ensure_parsed()
        for event in self._events:
            data = event.get("data", {})
            if isinstance(data, dict) and "request_id" in data:
                return data["request_id"]
        return None

    @property
    def events(self) -> list[dict[str, Any]]:
        """All accumulated events (triggers full parse if needed)."""
        self._ensure_parsed()
        return self._events
