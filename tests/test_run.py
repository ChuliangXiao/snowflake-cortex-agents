"""Tests for core/run module."""

import pytest

from cortex_agents.base import SnowflakeAPIError
from cortex_agents.core.run import RunRequest, build_run_request


class TestRunRequest:
    """Tests for RunRequest dataclass."""

    def test_create_run_request(self):
        """Should create a valid run request."""
        req = RunRequest(
            endpoint="cortex/agent:run",
            payload={"messages": [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]},
        )
        assert req.endpoint == "cortex/agent:run"
        assert len(req.payload["messages"]) == 1

    def test_run_request_immutable(self):
        """RunRequest should be immutable (frozen dataclass)."""
        req = RunRequest(endpoint="cortex/agent:run", payload={})
        with pytest.raises(AttributeError):
            req.endpoint = "new_endpoint"  # type: ignore


class TestBuildRunRequest:
    """Tests for build_run_request function."""

    def test_simple_query_inline(self):
        """Should build request for simple query with inline config."""
        request = build_run_request(
            query="What is the revenue?",
            agent_name=None,
            database=None,
            schema=None,
            tool_choice=None,
            messages=None,
            thread_id=None,
            parent_message_id=None,
            inline_config={"models": {"orchestration": "claude-sonnet-4-6"}},
        )
        assert request.endpoint == "cortex/agent:run"
        assert len(request.payload["messages"]) == 1
        assert request.payload["messages"][0]["role"] == "user"
        assert request.payload["models"]["orchestration"] == "claude-sonnet-4-6"

    def test_saved_agent(self):
        """Should build request for saved agent."""
        request = build_run_request(
            query="What is the revenue?",
            agent_name="MY_AGENT",
            database="MY_DB",
            schema="MY_SCHEMA",
            tool_choice=None,
            messages=None,
            thread_id=None,
            parent_message_id=None,
        )
        assert request.endpoint == "databases/MY_DB/schemas/MY_SCHEMA/agents/MY_AGENT:run"
        assert len(request.payload["messages"]) == 1

    def test_with_thread_id(self):
        """Should include thread_id and parent_message_id in payload."""
        request = build_run_request(
            query="Continue conversation",
            agent_name="MY_AGENT",
            database="DB",
            schema="SCHEMA",
            tool_choice=None,
            messages=None,
            thread_id=123,
            parent_message_id=456,
        )
        assert request.payload["thread_id"] == 123
        assert request.payload["parent_message_id"] == 456

    def test_with_tool_choice(self):
        """Should include tool_choice in payload."""
        tool_choice = {"type": "function", "function": {"name": "get_weather"}}
        request = build_run_request(
            query="What's the weather?",
            agent_name=None,
            database=None,
            schema=None,
            tool_choice=tool_choice,
            messages=None,
            thread_id=None,
            parent_message_id=None,
        )
        assert request.payload["tool_choice"] == tool_choice

    def test_with_history(self):
        """Should include message history."""
        history = [
            {"role": "user", "content": [{"type": "text", "text": "First question"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "First response"}]},
        ]
        request = build_run_request(
            query="Second question",
            agent_name=None,
            database=None,
            schema=None,
            tool_choice=None,
            messages=history,
            thread_id=None,
            parent_message_id=None,
        )
        assert len(request.payload["messages"]) == 3

    def test_inline_config_models(self):
        """Should include models from inline_config."""
        request = build_run_request(
            query="Test",
            agent_name=None,
            database=None,
            schema=None,
            tool_choice=None,
            messages=None,
            thread_id=None,
            parent_message_id=None,
            inline_config={"models": {"orchestration": "gpt-4"}},
        )
        assert request.payload["models"]["orchestration"] == "gpt-4"

    def test_inline_config_instructions(self):
        """Should include instructions from inline_config."""
        request = build_run_request(
            query="Test",
            agent_name=None,
            database=None,
            schema=None,
            tool_choice=None,
            messages=None,
            thread_id=None,
            parent_message_id=None,
            inline_config={"instructions": {"system": "You are helpful"}},
        )
        assert request.payload["instructions"]["system"] == "You are helpful"

    def test_inline_config_tools(self):
        """Should include tools from inline_config."""
        tools = [{"type": "function", "function": {"name": "get_weather"}}]
        request = build_run_request(
            query="Test",
            agent_name=None,
            database=None,
            schema=None,
            tool_choice=None,
            messages=None,
            thread_id=None,
            parent_message_id=None,
            inline_config={"tools": tools},
        )
        assert request.payload["tools"] == tools

    def test_inline_config_tool_choice_no_override(self):
        """Should use tool_choice from inline_config when parameter is None."""
        inline_tool_choice = {"type": "auto"}
        request = build_run_request(
            query="Test",
            agent_name=None,
            database=None,
            schema=None,
            tool_choice=None,
            messages=None,
            thread_id=None,
            parent_message_id=None,
            inline_config={"tool_choice": inline_tool_choice},
        )
        assert request.payload["tool_choice"] == inline_tool_choice

    def test_tool_choice_parameter_overrides_inline_config(self):
        """Should use tool_choice parameter over inline_config."""
        param_tool_choice = {"type": "function", "function": {"name": "specific"}}
        inline_tool_choice = {"type": "auto"}
        request = build_run_request(
            query="Test",
            agent_name=None,
            database=None,
            schema=None,
            tool_choice=param_tool_choice,
            messages=None,
            thread_id=None,
            parent_message_id=None,
            inline_config={"tool_choice": inline_tool_choice},
        )
        assert request.payload["tool_choice"] == param_tool_choice

    def test_inline_config_filters_invalid_keys(self):
        """Should only include allowed keys from inline_config."""
        request = build_run_request(
            query="Test",
            agent_name=None,
            database=None,
            schema=None,
            tool_choice=None,
            messages=None,
            thread_id=None,
            parent_message_id=None,
            inline_config={
                "models": {"orchestration": "gpt-4"},
                "invalid_key": "should_be_ignored",
            },
        )
        assert "models" in request.payload
        assert "invalid_key" not in request.payload

    def test_raises_on_thread_id_without_parent_message_id(self):
        """Should raise error when thread_id provided without parent_message_id."""
        with pytest.raises(SnowflakeAPIError, match="parent_message_id is required"):
            build_run_request(
                query="Test",
                agent_name=None,
                database=None,
                schema=None,
                tool_choice=None,
                messages=None,
                thread_id=123,
                parent_message_id=None,
            )

    def test_raises_on_agent_name_without_database(self):
        """Should raise error when agent_name provided without database."""
        with pytest.raises(SnowflakeAPIError, match="database and schema are required"):
            build_run_request(
                query="Test",
                agent_name="MY_AGENT",
                database=None,
                schema="SCHEMA",
                tool_choice=None,
                messages=None,
                thread_id=None,
                parent_message_id=None,
            )

    def test_raises_on_agent_name_without_schema(self):
        """Should raise error when agent_name provided without schema."""
        with pytest.raises(SnowflakeAPIError, match="database and schema are required"):
            build_run_request(
                query="Test",
                agent_name="MY_AGENT",
                database="DB",
                schema=None,
                tool_choice=None,
                messages=None,
                thread_id=None,
                parent_message_id=None,
            )

    def test_thread_id_zero_is_valid(self):
        """Should accept thread_id of 0 with parent_message_id of 0."""
        request = build_run_request(
            query="First message",
            agent_name=None,
            database=None,
            schema=None,
            tool_choice=None,
            messages=None,
            thread_id=0,
            parent_message_id=0,
        )
        assert request.payload["thread_id"] == 0
        assert request.payload["parent_message_id"] == 0
