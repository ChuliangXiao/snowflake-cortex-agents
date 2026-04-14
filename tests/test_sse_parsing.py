"""Tests for SSE parsing via BaseSSEResponse and AgentResponse.

Uses inline SSE fixtures to verify:
- SSE line-level framing (event:/data:/blank-line protocol)
- [DONE] sentinel handling
- JSON decode errors
- Multi-block text concatenation
- Event type simplification
- request_id extraction from headers
- Non-streaming (single JSON) path
- AgentResponse convenience properties (text, sql, thinking, charts, tables, suggested_queries)
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from cortex_agents._base_response import BaseSSEResponse
from cortex_agents.core.response import AgentResponse, EventType

# ---------------------------------------------------------------------------
# Helpers to build fake streaming responses from raw SSE text
# ---------------------------------------------------------------------------


class FakeHTTPResponse:
    """Minimal stand-in for httpx.Response used inside the SSE context manager."""

    def __init__(self, sse_text: str, headers: dict[str, str] | None = None):
        self._lines = sse_text.splitlines()
        self.headers = headers or {}
        self.status_code = 200

    def raise_for_status(self) -> None:
        pass

    def iter_lines(self):
        return iter(self._lines)


class FakeAsyncHTTPResponse:
    """Minimal async stand-in for httpx.Response used by async SSE parsing."""

    def __init__(self, sse_text: str, headers: dict[str, str] | None = None):
        self._lines = sse_text.splitlines()
        self.headers = headers or {}
        self.status_code = 200

    def raise_for_status(self) -> None:
        pass

    async def aiter_lines(self):
        for line in self._lines:
            yield line


@contextmanager
def _fake_stream(sse_text: str, headers: dict[str, str] | None = None):
    """Context-manager that yields a FakeHTTPResponse."""
    yield FakeHTTPResponse(sse_text, headers)


def _make_response(sse_text: str, headers: dict[str, str] | None = None, cls=AgentResponse) -> AgentResponse:
    """Build a streaming AgentResponse backed by fake SSE text."""
    return cls(lambda: _fake_stream(sse_text, headers), stream=True)


def _make_non_streaming_response(payload: dict[str, Any]) -> AgentResponse:
    """Build a non-streaming AgentResponse."""
    return AgentResponse(payload, stream=False)


def _make_counted_response(
    sse_text: str,
    headers: dict[str, str] | None = None,
) -> tuple[AgentResponse, dict[str, int]]:
    """Build a response whose stream-open count can be asserted in tests."""
    open_count = {"count": 0}

    @contextmanager
    def counted_stream():
        open_count["count"] += 1
        yield FakeHTTPResponse(sse_text, headers)

    return AgentResponse(lambda: counted_stream(), stream=True), open_count


def _make_counted_async_response(
    sse_text: str,
    headers: dict[str, str] | None = None,
) -> tuple[AgentResponse, dict[str, int]]:
    """Build an async response whose stream-open count can be asserted in tests."""
    open_count = {"count": 0}

    @asynccontextmanager
    async def counted_stream():
        open_count["count"] += 1
        yield FakeAsyncHTTPResponse(sse_text, headers)

    return AgentResponse(lambda: counted_stream(), stream=True, is_async=True), open_count


# ---------------------------------------------------------------------------
# SSE fixtures
# ---------------------------------------------------------------------------

SIMPLE_TEXT_SSE = """\
event: response.text.delta
data: {"content_index":0,"sequence_number":1,"text":"Hello"}

event: response.text.delta
data: {"content_index":0,"sequence_number":2,"text":" world"}

event: response.text
data: {"content_index":0,"sequence_number":3,"text":"Hello world"}

event: done
data: [DONE]
"""

MULTI_BLOCK_TEXT_SSE = """\
event: response.text.delta
data: {"content_index":0,"sequence_number":1,"text":"Block one"}

event: response.text
data: {"content_index":0,"sequence_number":2,"text":"Block one"}

event: response.text.delta
data: {"content_index":2,"sequence_number":3,"text":"Block two"}

event: response.text
data: {"content_index":2,"sequence_number":4,"text":"Block two"}

event: done
data: [DONE]
"""

THINKING_SSE = """\
event: response.thinking.delta
data: {"content_index":1,"sequence_number":1,"text":"Let me "}

event: response.thinking.delta
data: {"content_index":1,"sequence_number":2,"text":"think..."}

event: response.text.delta
data: {"content_index":2,"sequence_number":3,"text":"Answer"}

event: response.text
data: {"content_index":2,"sequence_number":4,"text":"Answer"}

event: done
data: [DONE]
"""

SQL_SSE = (
    "event: response.tool_result\n"
    'data: {"content":[{"json":{"sql":"SELECT 1","query_id":"qid-123","text":"Generated SQL"},'
    '"type":"json"}],"name":"analyst","tool_use_id":"tu_1",'
    '"type":"cortex_analyst_text_to_sql","status":"success","sequence_number":1}\n\n'
    "event: response.text.delta\n"
    'data: {"content_index":2,"sequence_number":2,"text":"Here is the result."}\n\n'
    "event: response.text\n"
    'data: {"content_index":2,"sequence_number":3,"text":"Here is the result."}\n\n'
    "event: done\n"
    "data: [DONE]\n"
)

TABLE_AND_CHART_SSE = (
    "event: response.text.delta\n"
    'data: {"content_index":0,"sequence_number":1,"text":"Summary"}\n\n'
    "event: response.text\n"
    'data: {"content_index":0,"sequence_number":2,"text":"Summary"}\n\n'
    "event: response.table\n"
    'data: {"query_id":"qid-t","result_set":{"data":[["a","1"]],'
    '"resultSetMetaData":{"numRows":1}},"title":"T1","tool_use_id":"tu_1","sequence_number":3}\n\n'
    "event: response.chart\n"
    'data: {"chart_spec":"{\\"mark\\":\\"bar\\"}","tool_use_id":"tu_2","sequence_number":4}\n\n'
    "event: response.suggested_queries\n"
    'data: {"content_index":5,"sequence_number":5,"suggested_queries":[{"query":"Follow up?"}]}\n\n'
    "event: done\n"
    "data: [DONE]\n"
)

WARNINGS_SSE = """\
event: response.warning
data: {"message":"low confidence","sequence_number":1}

event: response.text.delta
data: {"content_index":0,"sequence_number":2,"text":"ok"}

event: response.text
data: {"content_index":0,"sequence_number":3,"text":"ok"}

event: done
data: [DONE]
"""

METADATA_WITH_TOKENS_SSE = (
    "event: response.text.delta\n"
    'data: {"content_index":0,"sequence_number":1,"text":"hi"}\n\n'
    "event: response.text\n"
    'data: {"content_index":0,"sequence_number":2,"text":"hi"}\n\n'
    "event: response\n"
    'data: {"content":[{"text":"hi","type":"text"}],"metadata":{"usage":{"tokens_consumed":['
    '{"model_name":"test-model","input_tokens":{"total":100},"output_tokens":{"total":50}}]}},'
    '"role":"assistant","schema_version":"v2","sequence_number":3}\n\n'
    "event: done\n"
    "data: [DONE]\n"
)


# ===========================================================================
# Tests — BaseSSEResponse
# ===========================================================================


class TestBaseSSEParsing:
    """Low-level SSE framing tests."""

    def test_parse_simple_events(self):
        """Should parse event/data/blank-line framing."""
        resp = _make_response(SIMPLE_TEXT_SSE, cls=BaseSSEResponse)
        events = list(resp)
        # text.delta, text.delta, text, done
        assert len(events) == 4
        assert events[0]["type"] == "text.delta"
        assert events[0]["data"]["text"] == "Hello"
        assert events[1]["data"]["text"] == " world"
        assert events[2]["type"] == "text"
        assert events[3]["type"] == "done"

    def test_done_sentinel(self):
        """[DONE] should produce a done event with empty data dict."""
        resp = _make_response(SIMPLE_TEXT_SSE, cls=BaseSSEResponse)
        events = resp.events
        done = [e for e in events if e["type"] == "done"]
        assert len(done) == 1
        assert done[0]["data"] == {}

    def test_request_id_from_headers(self):
        """request_id should come from x-snowflake-request-id header."""
        resp = _make_response(
            SIMPLE_TEXT_SSE,
            headers={"x-snowflake-request-id": "abc-123"},
            cls=BaseSSEResponse,
        )
        resp._ensure_parsed()
        assert resp.request_id == "abc-123"

    def test_request_id_fallback_headers(self):
        """Should fall back through alternative header names."""
        for header in ("x-request-id", "request-id"):
            resp = _make_response(
                SIMPLE_TEXT_SSE,
                headers={header: "fall-" + header},
                cls=BaseSSEResponse,
            )
            resp._ensure_parsed()
            assert resp.request_id == "fall-" + header

    def test_json_decode_error(self):
        """Malformed JSON data should yield an error event."""
        bad_sse = "event: response.text.delta\ndata: {not json}\n\n"
        resp = _make_response(bad_sse, cls=BaseSSEResponse)
        events = list(resp)
        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "Failed to parse" in events[0]["data"]["message"]

    def test_simplify_strips_response_prefix(self):
        """Default _simplify_event strips 'response.' prefix."""
        resp = _make_response(SIMPLE_TEXT_SSE, cls=BaseSSEResponse)
        events = list(resp)
        assert events[0]["raw_type"] == "response.text.delta"
        assert events[0]["type"] == "text.delta"

    def test_events_property_triggers_parsing(self):
        """Accessing .events should consume the stream lazily."""
        resp = _make_response(SIMPLE_TEXT_SSE, cls=BaseSSEResponse)
        assert resp._parsed is False
        events = resp.events
        assert resp._parsed is True
        assert len(events) == 4

    def test_raw_data_preserved(self):
        """Each event should carry _raw_data with the original parsed JSON."""
        resp = _make_response(SIMPLE_TEXT_SSE, cls=BaseSSEResponse)
        events = resp.events
        for ev in events:
            if ev["type"] != "done":
                assert "_raw_data" in ev
                assert isinstance(ev["_raw_data"], dict)

    def test_request_id_then_full_parse_reuses_single_stream(self):
        """Capturing request_id should not reopen the underlying stream later."""
        resp, open_count = _make_counted_response(
            SIMPLE_TEXT_SSE,
            headers={"x-snowflake-request-id": "abc-123"},
        )

        assert resp.request_id == "abc-123"
        assert resp.text == "Hello world"
        assert open_count["count"] == 1

    def test_partial_iteration_then_property_access_reuses_single_stream(self):
        """Finishing a partially consumed stream should continue the same request."""
        resp, open_count = _make_counted_response(SIMPLE_TEXT_SSE)

        iterator = iter(resp)
        first_event = next(iterator)

        assert first_event["type"] == "text.delta"
        assert resp.text == "Hello world"
        assert len(resp.events) == 4
        assert open_count["count"] == 1

    def test_async_response_reuses_single_stream(self):
        """Async responses should resume the same stream after partial consumption."""

        async def run_scenario() -> None:
            resp, open_count = _make_counted_async_response(
                SIMPLE_TEXT_SSE,
                headers={"x-snowflake-request-id": "async-123"},
            )

            async for event in resp:
                assert event["type"] == "text.delta"
                break

            collected = []
            async for event in resp:
                collected.append(event)

            assert open_count["count"] == 1
            assert resp.request_id == "async-123"
            assert resp.text == "Hello world"
            assert len(collected) == 4

        asyncio.run(run_scenario())


# ===========================================================================
# Tests — AgentResponse properties
# ===========================================================================


class TestAgentResponseText:
    """Text extraction from streaming events."""

    def test_simple_text(self):
        resp = _make_response(SIMPLE_TEXT_SSE)
        assert resp.text == "Hello world"

    def test_multi_block_text(self):
        """Multiple response.text events should be concatenated."""
        resp = _make_response(MULTI_BLOCK_TEXT_SSE)
        assert "Block one" in resp.text
        assert "Block two" in resp.text

    def test_thinking(self):
        """thinking property should concatenate thinking deltas."""
        resp = _make_response(THINKING_SSE)
        assert "Let me think..." in resp.thinking


class TestAgentResponseSQL:
    """SQL extraction from tool_result events."""

    def test_sql_from_tool_result(self):
        resp = _make_response(SQL_SSE)
        assert resp.sql == "SELECT 1"

    def test_query_id(self):
        resp = _make_response(SQL_SSE)
        assert resp.query_id == "qid-123"


class TestAgentResponseRichContent:
    """Charts, tables, suggested queries."""

    def test_get_tables(self):
        resp = _make_response(TABLE_AND_CHART_SSE)
        tables = resp.get_tables()
        assert len(tables) == 1
        assert tables[0]["title"] == "T1"

    def test_get_charts(self):
        resp = _make_response(TABLE_AND_CHART_SSE)
        charts = resp.get_charts()
        assert len(charts) == 1
        assert '"mark"' in charts[0]["chart_spec"]

    def test_get_suggested_queries(self):
        resp = _make_response(TABLE_AND_CHART_SSE)
        sq = resp.get_suggested_queries()
        assert len(sq) == 1
        assert sq[0]["query"] == "Follow up?"


class TestAgentResponseWarnings:
    """Warning extraction."""

    def test_get_warnings(self):
        resp = _make_response(WARNINGS_SSE)
        warnings = resp.get_warnings()
        assert len(warnings) == 1
        assert warnings[0] == "low confidence"


class TestAgentResponseMetadata:
    """Token usage from metadata."""

    def test_get_token_usage(self):
        resp = _make_response(METADATA_WITH_TOKENS_SSE)
        usage = resp.get_token_usage()
        assert usage is not None
        # get_token_usage returns the 'usage' dict, which has 'tokens_consumed' list
        assert "tokens_consumed" in usage
        assert usage["tokens_consumed"][0]["model_name"] == "test-model"

    def test_get_metadata(self):
        resp = _make_response(METADATA_WITH_TOKENS_SSE)
        # get_metadata looks for events with type=="metadata", but the
        # final "response" event has raw_type=="response" and type=="response".
        # So get_metadata returns [] here.  The data lives in get_final_response.
        final = resp.get_final_response()
        assert final is not None
        assert "usage" in final["metadata"]


class TestAgentResponseNonStreaming:
    """Non-streaming (single JSON) response path."""

    def test_non_streaming_text(self):
        payload = {
            "content": [{"text": "non-stream answer", "type": "text"}],
            "metadata": {},
            "role": "assistant",
            "schema_version": "v2",
        }
        resp = _make_non_streaming_response(payload)
        events = resp.events
        assert len(events) == 1
        assert events[0]["type"] == "response"


# ===========================================================================
# Tests — EventType enum
# ===========================================================================


class TestEventTypeEnum:
    """EventType values unchanged after refactor."""

    def test_all_values(self):
        assert EventType.RESPONSE_TEXT_DELTA == "response.text.delta"
        assert EventType.RESPONSE_TABLE == "response.table"
        assert EventType.RESPONSE_CHART == "response.chart"
        assert EventType.DONE == "done"
        assert EventType.RESPONSE_SUGGESTED_QUERIES == "response.suggested_queries"
        assert EventType.RESPONSE_WARNING == "response.warning"
