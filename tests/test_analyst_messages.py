"""Tests for _analyst_messages module."""

import pytest

from cortex_agents._analyst_messages import normalize_analyst_messages


class TestNormalizeAnalystMessages:
    """Tests for normalize_analyst_messages function."""

    def test_valid_simple_user_message(self):
        """Should accept a simple valid user message."""
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]
        result = normalize_analyst_messages(messages)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"][0]["text"] == "Hello"

    def test_valid_conversation(self):
        """Should accept a valid multi-turn conversation."""
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "What is the revenue?"}]},
            {"role": "analyst", "content": [{"type": "sql", "statement": "SELECT SUM(revenue) FROM sales"}]},
            {"role": "user", "content": [{"type": "text", "text": "Show me by region"}]},
        ]
        result = normalize_analyst_messages(messages)
        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "analyst"
        assert result[2]["role"] == "user"

    def test_analyst_with_text_content(self):
        """Should accept analyst message with text content."""
        messages = [
            {"role": "analyst", "content": [{"type": "text", "text": "Here are the results"}]},
            {"role": "user", "content": [{"type": "text", "text": "Thanks"}]},
        ]
        result = normalize_analyst_messages(messages)
        assert len(result) == 2
        assert result[0]["content"][0]["type"] == "text"

    def test_analyst_with_suggestions(self):
        """Should accept analyst message with suggestions."""
        messages = [
            {
                "role": "analyst",
                "content": [{"type": "suggestions", "suggestions": ["Option 1", "Option 2"]}],
            },
            {"role": "user", "content": [{"type": "text", "text": "Option 1"}]},
        ]
        result = normalize_analyst_messages(messages)
        assert len(result) == 2
        assert result[0]["content"][0]["type"] == "suggestions"

    def test_rejects_empty_list(self):
        """Should reject empty message list."""
        with pytest.raises(ValueError, match="must be a non-empty list"):
            normalize_analyst_messages([])

    def test_rejects_non_list(self):
        """Should reject non-list input."""
        with pytest.raises(ValueError, match="must be a non-empty list"):
            normalize_analyst_messages("not a list")  # type: ignore

    def test_rejects_non_dict_message(self):
        """Should reject non-dictionary messages."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            normalize_analyst_messages(["not a dict"])  # type: ignore

    def test_rejects_invalid_role(self):
        """Should reject invalid role."""
        messages = [{"role": "system", "content": [{"type": "text", "text": "Hello"}]}]
        with pytest.raises(ValueError, match="role must be 'user' or 'analyst'"):
            normalize_analyst_messages(messages)

    def test_rejects_last_message_not_user(self):
        """Should reject when last message is not from user."""
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "Hello"}]},
            {"role": "analyst", "content": [{"type": "text", "text": "Response"}]},
        ]
        with pytest.raises(ValueError, match="last message.*must have role 'user'"):
            normalize_analyst_messages(messages)

    def test_rejects_missing_content(self):
        """Should reject message without content."""
        messages = [{"role": "user"}]
        with pytest.raises(ValueError, match="non-empty 'content' list"):
            normalize_analyst_messages(messages)

    def test_rejects_empty_content_list(self):
        """Should reject message with empty content list."""
        messages = [{"role": "user", "content": []}]
        with pytest.raises(ValueError, match="non-empty 'content' list"):
            normalize_analyst_messages(messages)

    def test_rejects_non_dict_content_item(self):
        """Should reject content items that are not dictionaries."""
        messages = [{"role": "user", "content": ["not a dict"]}]
        with pytest.raises(ValueError, match="content items must be dictionaries"):
            normalize_analyst_messages(messages)

    def test_rejects_user_non_text_content(self):
        """Should reject user messages with non-text content type."""
        messages = [{"role": "user", "content": [{"type": "sql", "statement": "SELECT 1"}]}]
        with pytest.raises(ValueError, match="User messages currently support only text content"):
            normalize_analyst_messages(messages)

    def test_rejects_user_empty_text(self):
        """Should reject user message with empty text."""
        messages = [{"role": "user", "content": [{"type": "text", "text": "   "}]}]
        with pytest.raises(ValueError, match="User message text must be a non-empty string"):
            normalize_analyst_messages(messages)

    def test_rejects_user_non_string_text(self):
        """Should reject user message with non-string text."""
        messages = [{"role": "user", "content": [{"type": "text", "text": 123}]}]
        with pytest.raises(ValueError, match="User message text must be a non-empty string"):
            normalize_analyst_messages(messages)

    def test_rejects_analyst_invalid_content_type(self):
        """Should reject analyst message with invalid content type."""
        messages = [
            {"role": "analyst", "content": [{"type": "invalid", "data": "something"}]},
            {"role": "user", "content": [{"type": "text", "text": "Ok"}]},
        ]
        with pytest.raises(ValueError, match="Analyst messages support content types"):
            normalize_analyst_messages(messages)

    def test_rejects_analyst_text_without_string(self):
        """Should reject analyst text content without string text field."""
        messages = [
            {"role": "analyst", "content": [{"type": "text", "text": 123}]},
            {"role": "user", "content": [{"type": "text", "text": "Ok"}]},
        ]
        with pytest.raises(ValueError, match="Analyst text content must include a string 'text' field"):
            normalize_analyst_messages(messages)

    def test_rejects_analyst_sql_without_statement(self):
        """Should reject analyst sql content without statement field."""
        messages = [
            {"role": "analyst", "content": [{"type": "sql", "statement": 123}]},
            {"role": "user", "content": [{"type": "text", "text": "Ok"}]},
        ]
        with pytest.raises(ValueError, match="Analyst sql content must include a string 'statement' field"):
            normalize_analyst_messages(messages)

    def test_rejects_analyst_suggestions_without_list(self):
        """Should reject analyst suggestions content without list."""
        messages = [
            {"role": "analyst", "content": [{"type": "suggestions", "suggestions": "not a list"}]},
            {"role": "user", "content": [{"type": "text", "text": "Ok"}]},
        ]
        with pytest.raises(ValueError, match="Analyst suggestions content must include a list 'suggestions'"):
            normalize_analyst_messages(messages)

    def test_returns_deep_copy(self):
        """Should return a deep copy, not modifying original."""
        messages = [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]
        result = normalize_analyst_messages(messages)
        result[0]["role"] = "analyst"
        assert messages[0]["role"] == "user"  # Original unchanged

    def test_multiple_content_items(self):
        """Should accept multiple content items in a message."""
        messages = [
            {
                "role": "analyst",
                "content": [
                    {"type": "text", "text": "Here's the query:"},
                    {"type": "sql", "statement": "SELECT * FROM table"},
                ],
            },
            {"role": "user", "content": [{"type": "text", "text": "Thanks"}]},
        ]
        result = normalize_analyst_messages(messages)
        assert len(result) == 2
        assert len(result[0]["content"]) == 2
