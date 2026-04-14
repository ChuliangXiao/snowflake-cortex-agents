"""Run execution helpers for Cortex Agents."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, TypedDict

from ..base import SnowflakeAPIError
from ._messages import prepare_agent_messages
from ._transport import AsyncTransport, SyncTransport
from .response import AgentResponse

_ALLOWED_INLINE_KEYS = {
    "models",
    "instructions",
    "orchestration",
    "tools",
    "tool_resources",
    "tool_choice",
}


class AgentInlineConfig(TypedDict, total=False):
    """Typed configuration for inline (ephemeral) agent runs.

    All keys are optional. Only the keys listed here are forwarded to
    the Cortex Agent Run API payload.
    """

    models: dict[str, Any]
    instructions: dict[str, Any]
    orchestration: dict[str, Any]
    tools: list[dict[str, Any]]
    tool_resources: dict[str, Any]
    tool_choice: dict[str, Any]


@dataclass(frozen=True)
class RunRequest:
    """Resolved endpoint and payload for a Cortex Agent :run invocation.

    Attributes:
        endpoint: API endpoint URL for the run request.
        payload: Request payload containing messages and configuration.
    """

    endpoint: str
    payload: dict[str, Any]


def build_run_request(
    *,
    query: str | None,
    agent_name: str | None,
    database: str | None,
    schema: str | None,
    tool_choice: dict[str, Any] | None,
    messages: Iterable[dict[str, Any]] | None,
    thread_id: str | int | None,
    parent_message_id: str | int | None,
    inline_config: Mapping[str, Any] | None = None,
    stream: bool = True,
) -> RunRequest:
    """Build the endpoint and payload for the Cortex Agent Run API.

    Constructs a RunRequest containing the proper endpoint URL and request
    payload based on whether using a saved agent or inline configuration.

    Args:
        query: User query string.
        agent_name: Name of saved agent to run (optional).
        database: Database name (required if agent_name provided).
        schema: Schema name (required if agent_name provided).
        tool_choice: Tool selection strategy (optional).
        messages: Conversation history messages (optional).
        thread_id: Thread ID for multi-turn conversations (optional).
        parent_message_id: Parent message ID in thread (required if thread_id set).
        inline_config: Inline agent configuration for ephemeral runs (optional).

    Returns:
        RunRequest with endpoint URL and payload.

    Raises:
        SnowflakeAPIError: If parent_message_id is missing when thread_id is
            provided, or if database/schema are missing with agent_name.

    Examples:
        ```python
        # Saved agent
        request = build_run_request(
            query="What's the revenue?",
            agent_name="MY_AGENT",
            database="DB",
            schema="SCHEMA"
        )

        # Inline configuration
        request = build_run_request(
            query="Analyze this data",
            inline_config={
                "models": {"orchestration": "claude-sonnet-4-6"},
                "instructions": {"system": "You are helpful"}
            }
        )
        ```
    """
    payload: dict[str, Any] = {
        "messages": prepare_agent_messages(question=query, history=messages),
        "stream": stream,
    }

    if thread_id is not None:
        if parent_message_id is None:
            raise SnowflakeAPIError(
                "parent_message_id is required when thread_id is provided. Use 0 for the first message in the thread."
            )
        payload["thread_id"] = thread_id
        payload["parent_message_id"] = parent_message_id

    if tool_choice is not None:
        payload["tool_choice"] = tool_choice

    if inline_config:
        for key in _ALLOWED_INLINE_KEYS:
            if key in inline_config and key != "tool_choice":
                payload[key] = inline_config[key]

        if "tool_choice" in inline_config and tool_choice is None:
            payload["tool_choice"] = inline_config["tool_choice"]

    if agent_name:
        if not database or not schema:
            raise SnowflakeAPIError("database and schema are required when using a saved agent (agent_name)")
        endpoint = f"databases/{database}/schemas/{schema}/agents/{agent_name}:run"
    else:
        endpoint = "cortex/agent:run"

    return RunRequest(endpoint=endpoint, payload=payload)


class AgentRun:
    """Execute synchronous Cortex Agent runs."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def run(
        self,
        *,
        query: str | None = None,
        agent_name: str | None = None,
        database: str | None = None,
        schema: str | None = None,
        thread_id: str | int | None = None,
        parent_message_id: str | int | None = None,
        tool_choice: dict[str, Any] | None = None,
        messages: Iterable[dict[str, Any]] | None = None,
        agent_config: Mapping[str, Any] | None = None,
        stream: bool = True,
    ) -> AgentResponse:
        """Execute a Cortex Agent run.

        Args:
            query: User query string.
            agent_name: Name of saved agent to run (optional).
            database: Database name (required if agent_name provided).
            schema: Schema name (required if agent_name provided).
            thread_id: Thread ID for multi-turn conversations (optional).
            parent_message_id: Parent message ID in thread (required if thread_id set).
            tool_choice: Tool selection strategy (optional).
            messages: Conversation history messages (optional).
            agent_config: Inline agent configuration for ephemeral runs (optional).

        Returns:
            AgentResponse with streaming support.

        Raises:
            SnowflakeAPIError: If the request fails or parameters are invalid.

        Examples:
            ```python
            # Run saved agent
            response = runner.run(
                query="What's the revenue?",
                agent_name="MY_AGENT",
                database="DB",
                schema="SCHEMA"
            )

            # Stream events
            for event in response:
                print(event)
            ```
        """
        request = build_run_request(
            query=query,
            agent_name=agent_name,
            database=database,
            schema=schema,
            tool_choice=tool_choice,
            messages=messages,
            thread_id=thread_id,
            parent_message_id=parent_message_id,
            inline_config=dict(agent_config) if agent_config else None,
            stream=stream,
        )

        transport_result = self._transport.post(request.endpoint, request.payload, stream=stream)
        return AgentResponse(transport_result, stream=stream)


class AsyncAgentRun:
    """Execute asynchronous Cortex Agent runs."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def run(
        self,
        *,
        query: str | None = None,
        agent_name: str | None = None,
        database: str | None = None,
        schema: str | None = None,
        thread_id: str | int | None = None,
        parent_message_id: str | int | None = None,
        tool_choice: dict[str, Any] | None = None,
        messages: Iterable[dict[str, Any]] | None = None,
        agent_config: Mapping[str, Any] | None = None,
        stream: bool = True,
    ) -> AgentResponse:
        """Execute a Cortex Agent run (async).

        Args:
            query: User query string.
            agent_name: Name of saved agent to run (optional).
            database: Database name (required if agent_name provided).
            schema: Schema name (required if agent_name provided).
            thread_id: Thread ID for multi-turn conversations (optional).
            parent_message_id: Parent message ID in thread (required if thread_id set).
            tool_choice: Tool selection strategy (optional).
            messages: Conversation history messages (optional).
            agent_config: Inline agent configuration for ephemeral runs (optional).

        Returns:
            AgentResponse with async streaming support.

        Raises:
            SnowflakeAPIError: If the request fails or parameters are invalid.

        Examples:
            ```python
            # Run saved agent
            response = await runner.run(
                query="What's the revenue?",
                agent_name="MY_AGENT",
                database="DB",
                schema="SCHEMA"
            )

            # Stream events asynchronously
            async for event in response:
                print(event)
            ```
        """
        request = build_run_request(
            query=query,
            agent_name=agent_name,
            database=database,
            schema=schema,
            tool_choice=tool_choice,
            messages=messages,
            thread_id=thread_id,
            parent_message_id=parent_message_id,
            inline_config=dict(agent_config) if agent_config else None,
            stream=stream,
        )

        transport_result = await self._transport.post(request.endpoint, request.payload, stream=stream)
        return AgentResponse(transport_result, stream=stream, is_async=True)
