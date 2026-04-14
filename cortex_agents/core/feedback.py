"""Feedback submission helpers for Cortex Agents."""

from __future__ import annotations

from typing import Any


class AgentFeedback:
    """Submit feedback for synchronous Cortex Agent responses."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def submit_feedback(
        self,
        agent_name: str,
        database: str,
        schema: str,
        *,
        positive: bool,
        feedback_message: str | None = None,
        categories: list[str] | None = None,
        orig_request_id: str | None = None,
        thread_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Submit user feedback for a Cortex Agent response.

        Args:
            agent_name: Agent name.
            database: Database name.
            schema: Schema name.
            positive: True for positive feedback, False for negative.
            feedback_message: Optional text feedback from user.
            categories: Optional list of feedback categories.
            orig_request_id: Original request ID from the agent response.
            thread_id: Thread ID if feedback is for a threaded conversation.

        Returns:
            Response dictionary confirming feedback submission.

        Raises:
            SnowflakeAPIError: If the request fails.

        Examples:
            ```python
            client.submit_feedback(
                agent_name="MY_AGENT",
                database="DB",
                schema="SCHEMA",
                positive=True,
                feedback_message="Very helpful response!",
                orig_request_id=response.request_id
            )
            ```
        """
        payload: dict[str, Any] = {"positive": positive}
        if orig_request_id:
            payload["orig_request_id"] = orig_request_id
        if feedback_message:
            payload["feedback_message"] = feedback_message
        if categories:
            payload["categories"] = categories
        if thread_id is not None:
            payload["thread_id"] = thread_id

        endpoint = f"databases/{database}/schemas/{schema}/agents/{agent_name}:feedback"
        return self._transport.post(endpoint, payload)


class AsyncAgentFeedback:
    """Submit feedback for asynchronous Cortex Agent responses."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def submit_feedback(
        self,
        agent_name: str,
        database: str,
        schema: str,
        *,
        positive: bool,
        feedback_message: str | None = None,
        categories: list[str] | None = None,
        orig_request_id: str | None = None,
        thread_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Submit user feedback for a Cortex Agent response (async).

        Args:
            agent_name: Agent name.
            database: Database name.
            schema: Schema name.
            positive: True for positive feedback, False for negative.
            feedback_message: Optional text feedback from user.
            categories: Optional list of feedback categories.
            orig_request_id: Original request ID from the agent response.
            thread_id: Thread ID if feedback is for a threaded conversation.

        Returns:
            Response dictionary confirming feedback submission.

        Raises:
            SnowflakeAPIError: If the request fails.

        Examples:
            ```python
            await client.submit_feedback(
                agent_name="MY_AGENT",
                database="DB",
                schema="SCHEMA",
                positive=True,
                feedback_message="Very helpful response!",
                orig_request_id=response.request_id
            )
            ```
        """
        payload: dict[str, Any] = {"positive": positive}
        if orig_request_id:
            payload["orig_request_id"] = orig_request_id
        if feedback_message:
            payload["feedback_message"] = feedback_message
        if categories:
            payload["categories"] = categories
        if thread_id is not None:
            payload["thread_id"] = thread_id

        endpoint = f"databases/{database}/schemas/{schema}/agents/{agent_name}:feedback"
        return await self._transport.post(endpoint, payload)
