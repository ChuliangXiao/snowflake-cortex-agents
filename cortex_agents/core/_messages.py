"""Utilities for constructing and validating Cortex Agent message payloads."""

from __future__ import annotations

from collections.abc import Iterable, MutableSequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from ..base import SnowflakeAPIError

_ALLOWED_ROLES = {"user", "assistant", "system", "tool"}


@dataclass(frozen=True)
class AgentMessage:
    """Typed representation of a Cortex Agent message entry."""

    role: str
    content: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {"role": self.role, "content": deepcopy(self.content)}


def _ensure_text_question(question: str) -> AgentMessage:
    if not isinstance(question, str) or not question.strip():
        raise SnowflakeAPIError("query must be a non-empty string when messages are not provided")
    return AgentMessage(role="user", content=[{"type": "text", "text": question.strip()}])


def _normalize_messages(messages: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for raw in messages:
        if not isinstance(raw, dict):
            raise SnowflakeAPIError("Each message must be a dictionary")

        role = raw.get("role")
        if role not in _ALLOWED_ROLES:
            raise SnowflakeAPIError("message role must be one of: user, assistant, system, tool")

        content = raw.get("content")
        if not isinstance(content, MutableSequence) or not content:
            raise SnowflakeAPIError("Each message must include a non-empty 'content' list")

        for item in content:
            if not isinstance(item, dict) or "type" not in item:
                raise SnowflakeAPIError("Each message content entry must include a 'type'")

        normalized.append(deepcopy(raw))

    return normalized


def prepare_agent_messages(
    *,
    question: str | None,
    history: Iterable[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Combine conversation history with the current user question.

    Args:
        question: Latest user question. May be None or blank when `history`
            already contains the trailing user message.
        history: Prior conversation messages to continue from.

    Returns:
        List of message dictionaries suitable for the Agent Run API.

    Raises:
        SnowflakeAPIError: If neither a question nor history with a trailing
            user message is provided, or if provided messages are invalid.
    """

    normalized_history: list[dict[str, Any]] = []

    if history:
        normalized_history = _normalize_messages(history)

    question_value = question.strip() if isinstance(question, str) else ""

    if question_value:
        normalized_history.append(_ensure_text_question(question_value).as_dict())
        return normalized_history

    if not normalized_history:
        raise SnowflakeAPIError("Either query must be provided or messages must include the latest user prompt")

    last_message = normalized_history[-1]
    if last_message.get("role") != "user":
        raise SnowflakeAPIError("When query is omitted, the final message in `messages` must have role 'user'")

    return normalized_history
