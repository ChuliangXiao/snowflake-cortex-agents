"""Internal helpers for Cortex Analyst message payload validation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_ALLOWED_ROLES = {"user", "analyst"}
_ANALYST_ALLOWED_TYPES = {"text", "sql", "suggestions"}


def normalize_analyst_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a deep copy of messages validated against Analyst REST API schema.

    Raises ValueError with a descriptive message when validation fails.
    """
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list of message objects")

    normalized: list[dict[str, Any]] = []
    last_index = len(messages) - 1

    for idx, message in enumerate(messages):
        if not isinstance(message, dict):
            raise ValueError("Each message must be a dictionary")

        role = message.get("role")
        if role not in _ALLOWED_ROLES:
            raise ValueError("message role must be 'user' or 'analyst'")

        if idx == last_index and role != "user":
            raise ValueError("The last message in the array must have role 'user'")

        content = message.get("content")
        if not isinstance(content, list) or not content:
            raise ValueError("Each message must include a non-empty 'content' list")

        normalized_message = deepcopy(message)
        normalized_content = normalized_message.get("content", [])

        for item in normalized_content:
            if not isinstance(item, dict):
                raise ValueError("message content items must be dictionaries")

            item_type = item.get("type")
            if role == "user":
                if item_type != "text":
                    raise ValueError("User messages currently support only text content")
                text = item.get("text")
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("User message text must be a non-empty string")
            else:
                if item_type not in _ANALYST_ALLOWED_TYPES:
                    raise ValueError("Analyst messages support content types: text, sql, suggestions")
                if item_type == "text" and not isinstance(item.get("text"), str):
                    raise ValueError("Analyst text content must include a string 'text' field")
                if item_type == "sql" and not isinstance(item.get("statement"), str):
                    raise ValueError("Analyst sql content must include a string 'statement' field")
                if item_type == "suggestions" and not isinstance(item.get("suggestions"), list):
                    raise ValueError("Analyst suggestions content must include a list 'suggestions'")

        normalized.append(normalized_message)

    return normalized
