"""Tests for core/_messages module."""

import pytest

from cortex_agents.base import SnowflakeAPIError
from cortex_agents.core._messages import AgentMessage, prepare_agent_messages


class TestAgentMessage:
    """Tests for AgentMessage dataclass."""

    def test_create_agent_message(self):
        """Should create a valid agent message."""
        msg = AgentMessage(role="user", content=[{"type": "text", "text": "Hello"}])
        assert msg.role == "user"
        assert len(msg.content) == 1
        assert msg.content[0]["text"] == "Hello"

    def test_as_dict(self):
        """Should convert to dictionary."""
        msg = AgentMessage(role="user", content=[{"type": "text", "text": "Hello"}])
        d = msg.as_dict()
        assert isinstance(d, dict)
        assert d["role"] == "user"
        assert d["content"][0]["text"] == "Hello"

    def test_as_dict_returns_deep_copy(self):
        """Should return a deep copy of content."""
        msg = AgentMessage(role="user", content=[{"type": "text", "text": "Hello"}])
        d = msg.as_dict()
        d["content"][0]["text"] = "Modified"
        assert msg.content[0]["text"] == "Hello"  # Original unchanged


class TestPrepareAgentMessages:
    """Tests for prepare_agent_messages function."""

    def test_simple_question_only(self):
        """Should accept just a question string."""
        result = prepare_agent_messages(question="What is the revenue?", history=None)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"][0]["text"] == "What is the revenue?"

    def test_question_with_whitespace_trimmed(self):
        """Should trim whitespace from question."""
        result = prepare_agent_messages(question="  Hello  ", history=None)
        assert result[0]["content"][0]["text"] == "Hello"

    def test_history_only(self):
        """Should accept history ending with user message."""
        history = [
            {"role": "user", "content": [{"type": "text", "text": "First question"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "First response"}]},
            {"role": "user", "content": [{"type": "text", "text": "Second question"}]},
        ]
        result = prepare_agent_messages(question=None, history=history)
        assert len(result) == 3
        assert result[-1]["role"] == "user"

    def test_history_with_new_question(self):
        """Should append new question to history."""
        history = [
            {"role": "user", "content": [{"type": "text", "text": "First question"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Response"}]},
        ]
        result = prepare_agent_messages(question="Next question", history=history)
        assert len(result) == 3
        assert result[-1]["role"] == "user"
        assert result[-1]["content"][0]["text"] == "Next question"

    def test_empty_string_question_with_history(self):
        """Should treat empty string as no question."""
        history = [{"role": "user", "content": [{"type": "text", "text": "Question"}]}]
        result = prepare_agent_messages(question="", history=history)
        assert len(result) == 1

    def test_none_question_with_history(self):
        """Should accept None question with valid history."""
        history = [{"role": "user", "content": [{"type": "text", "text": "Question"}]}]
        result = prepare_agent_messages(question=None, history=history)
        assert len(result) == 1

    def test_raises_on_no_input(self):
        """Should raise error when neither question nor history provided."""
        with pytest.raises(SnowflakeAPIError, match="Either query must be provided"):
            prepare_agent_messages(question=None, history=None)

    def test_raises_on_empty_question_no_history(self):
        """Should raise error on empty question with no history."""
        with pytest.raises(SnowflakeAPIError, match="Either query must be provided"):
            prepare_agent_messages(question="   ", history=None)

    def test_raises_on_history_not_ending_with_user(self):
        """Should raise error when history doesn't end with user message."""
        history = [
            {"role": "user", "content": [{"type": "text", "text": "Question"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Response"}]},
        ]
        with pytest.raises(SnowflakeAPIError, match="final message.*must have role 'user'"):
            prepare_agent_messages(question=None, history=history)

    def test_raises_on_invalid_message_not_dict(self):
        """Should raise error on non-dictionary messages."""
        history = ["not a dict"]  # type: ignore
        with pytest.raises(SnowflakeAPIError, match="must be a dictionary"):
            prepare_agent_messages(question="Test", history=history)

    def test_raises_on_invalid_role(self):
        """Should raise error on invalid role."""
        history = [{"role": "invalid", "content": [{"type": "text", "text": "Hello"}]}]
        with pytest.raises(SnowflakeAPIError, match="role must be one of"):
            prepare_agent_messages(question="Test", history=history)

    def test_raises_on_missing_content(self):
        """Should raise error on missing content."""
        history = [{"role": "user"}]
        with pytest.raises(SnowflakeAPIError, match="non-empty 'content' list"):
            prepare_agent_messages(question="Test", history=history)

    def test_raises_on_empty_content(self):
        """Should raise error on empty content list."""
        history = [{"role": "user", "content": []}]
        with pytest.raises(SnowflakeAPIError, match="non-empty 'content' list"):
            prepare_agent_messages(question="Test", history=history)

    def test_raises_on_content_item_without_type(self):
        """Should raise error on content items without type."""
        history = [{"role": "user", "content": [{"text": "Hello"}]}]
        with pytest.raises(SnowflakeAPIError, match="must include a 'type'"):
            prepare_agent_messages(question="Test", history=history)

    def test_accepts_system_role(self):
        """Should accept system role messages."""
        history = [
            {"role": "system", "content": [{"type": "text", "text": "System prompt"}]},
            {"role": "user", "content": [{"type": "text", "text": "User question"}]},
        ]
        result = prepare_agent_messages(question=None, history=history)
        assert len(result) == 2
        assert result[0]["role"] == "system"

    def test_accepts_tool_role(self):
        """Should accept tool role messages."""
        history = [
            {"role": "user", "content": [{"type": "text", "text": "Question"}]},
            {"role": "tool", "content": [{"type": "text", "text": "Tool result"}]},
            {"role": "user", "content": [{"type": "text", "text": "Follow up"}]},
        ]
        result = prepare_agent_messages(question=None, history=history)
        assert len(result) == 3
        assert result[1]["role"] == "tool"

    def test_returns_deep_copy_of_history(self):
        """Should return deep copy of history, not modify original."""
        history = [{"role": "user", "content": [{"type": "text", "text": "Original"}]}]
        result = prepare_agent_messages(question="New", history=history)
        result[0]["content"][0]["text"] = "Modified"
        assert history[0]["content"][0]["text"] == "Original"

    def test_multiple_content_items(self):
        """Should accept messages with multiple content items."""
        history = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Question"},
                    {"type": "image", "url": "http://example.com/image.jpg"},
                ],
            }
        ]
        result = prepare_agent_messages(question=None, history=history)
        assert len(result) == 1
        assert len(result[0]["content"]) == 2
