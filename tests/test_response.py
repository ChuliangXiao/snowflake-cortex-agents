"""Tests for core/response module."""

from cortex_agents.core.response import EventType


class TestEventType:
    """Tests for EventType enum."""

    def test_response_event_types(self):
        """Should have all expected response event types."""
        assert EventType.RESPONSE == "response"
        assert EventType.RESPONSE_TEXT == "response.text"
        assert EventType.RESPONSE_TEXT_DELTA == "response.text.delta"
        assert EventType.RESPONSE_TEXT_ANNOTATION == "response.text.annotation"
        assert EventType.RESPONSE_THINKING == "response.thinking"
        assert EventType.RESPONSE_THINKING_DELTA == "response.thinking.delta"
        assert EventType.RESPONSE_TOOL_USE == "response.tool_use"
        assert EventType.RESPONSE_TOOL_RESULT == "response.tool_result"
        assert EventType.RESPONSE_TOOL_RESULT_STATUS == "response.tool_result.status"
        assert EventType.RESPONSE_TOOL_RESULT_ANALYST_DELTA == "response.tool_result.analyst.delta"
        assert EventType.RESPONSE_TABLE == "response.table"
        assert EventType.RESPONSE_CHART == "response.chart"
        assert EventType.RESPONSE_STATUS == "response.status"

    def test_other_event_types(self):
        """Should have metadata, error, and trace event types."""
        assert EventType.METADATA == "metadata"
        assert EventType.ERROR == "error"
        assert EventType.EXECUTION_TRACE == "execution_trace"

    def test_event_type_is_string_enum(self):
        """EventType should inherit from str."""
        assert isinstance(EventType.RESPONSE, str)
        assert EventType.RESPONSE == "response"
