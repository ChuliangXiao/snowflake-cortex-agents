"""Async Snowflake Cortex Analyst API Client.
https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/rest-api

This module provides an async client for interacting with Snowflake's Cortex Analyst API.
Handles SQL generation from natural language using semantic models.
"""

import asyncio
import logging
from copy import deepcopy
from typing import Any

import httpx

from ._analyst_messages import normalize_analyst_messages
from ._analyst_response import AnalystResponse
from .base import BaseAgent, SnowflakeAPIError
from .core._transport import AsyncTransport

logger: logging.Logger = logging.getLogger(__name__)


class AsyncCortexAnalyst(BaseAgent):
    """Async client for Snowflake Cortex Analyst.

    Examples:
    ```python
    async with AsyncCortexAnalyst() as analyst:
        response = await analyst.message(
            "Which company had the most revenue?",
            semantic_model_file="@my_stage/model.yaml"
        )

        # Stream results
        async for event in response.astream():
            if event["type"] == "text.delta":
                print(event["data"]["text"], end="", flush=True)
    ```
    """

    def __init__(
        self,
        account_url: str | None = None,
        pat: str | None = None,
        enable_logging: bool = True,
        token_type: str | None = None,
    ) -> None:
        """Initialize the Async Cortex Analyst client."""
        super().__init__(account_url=account_url, pat=pat, enable_logging=enable_logging, token_type=token_type)
        self._client: httpx.AsyncClient | None = None
        self._transport: AsyncTransport | None = None

        if self._enable_logging:
            logger.info("AsyncCortexAnalyst initialized")

    async def __aenter__(self) -> "AsyncCortexAnalyst":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            headers=self._build_headers(),
            timeout=httpx.Timeout(connect=30.0, read=900.0, write=30.0, pool=30.0),
        )
        self._transport = AsyncTransport(
            client=self._client,
            build_url=self._get_url,
            log_request=self._log_request,
            log_response=self._log_response,
            logger=logger,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.aclose()

    def close(self) -> None:
        """Close the async client and cleanup resources."""
        if not self._client:
            return

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.aclose())
        else:
            raise SnowflakeAPIError("close() cannot run while the event loop is active; use 'await aclose()' instead")

    async def aclose(self) -> None:
        """Async close helper for use within a running event loop."""
        if self._client:
            await self._client.aclose()
            logger.debug("AsyncCortexAnalyst client closed")
            self._client = None
            self._transport = None

    def _ensure_transport(self) -> AsyncTransport:
        if not self._transport:
            raise SnowflakeAPIError("Client not initialized. Use async with context manager.")
        return self._transport

    async def message(
        self,
        question: str,
        semantic_model_file: str | None = None,
        semantic_model: str | None = None,
        semantic_view: str | None = None,
        semantic_models: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
        stream: bool = True,
    ) -> AnalystResponse:
        """Send a natural language question to Cortex Analyst (async).

        Args:
            question: Natural language question
            semantic_model_file: Path to semantic model file in stage (e.g., "@stage/model.yaml")
            semantic_model: Inline semantic model YAML string
            semantic_view: Name of semantic view (alternative to semantic_model_file)
            semantic_models: Collection of semantic model descriptors
            messages: Previous conversation messages for multi-turn conversations
            stream: Whether to request a streaming response (default True)

        Returns:
            AnalystResponse: Response with SQL, text, and streaming support

        Examples:
        ```python
        async with AsyncCortexAnalyst() as analyst:
            response = await analyst.message(
                "What was the total revenue last quarter?",
                semantic_model_file="@my_stage/revenue_model.yaml"
            )

            print(response.sql)
            print(response.text)
        ```
        """
        transport = self._ensure_transport()

        if not isinstance(question, str):
            raise SnowflakeAPIError("question must be a string")

        model_flags = [bool(semantic_model_file), bool(semantic_model), bool(semantic_view), bool(semantic_models)]
        if sum(model_flags) != 1:
            raise SnowflakeAPIError(
                "You must provide exactly one of semantic_model_file, semantic_model, semantic_view, or semantic_models"
            )

        if messages is None:
            default_messages = [{"role": "user", "content": [{"type": "text", "text": question}]}]
            try:
                payload_messages = normalize_analyst_messages(default_messages)
            except ValueError as exc:
                raise SnowflakeAPIError(str(exc)) from exc
        else:
            messages_with_question = deepcopy(messages)
            messages_with_question.append({"role": "user", "content": [{"type": "text", "text": question}]})
            try:
                payload_messages = normalize_analyst_messages(messages_with_question)
            except ValueError as exc:
                raise SnowflakeAPIError(str(exc)) from exc

        payload: dict[str, Any] = {"messages": payload_messages}

        if semantic_model_file:
            payload["semantic_model_file"] = semantic_model_file
        elif semantic_model:
            payload["semantic_model"] = semantic_model
        elif semantic_view:
            payload["semantic_view"] = semantic_view
        elif semantic_models:
            payload["semantic_models"] = semantic_models

        if stream:
            payload["stream"] = True

        response_payload = await transport.post("cortex/analyst/message", payload, stream=stream)
        return AnalystResponse(
            response_payload,
            stream=stream,
            is_async=True,
            request_messages=payload_messages,
        )

    async def suggest_questions(
        self,
        semantic_model_file: str | None = None,
        semantic_view: str | None = None,
        max_questions: int = 3,
    ) -> list[str]:
        """Get suggested questions based on semantic model (async).

        Args:
            semantic_model_file: Path to semantic model file
            semantic_view: Name of semantic view
            max_questions: Maximum number of questions to return

        Returns:
            list[str]: Suggested questions
        """
        transport = self._ensure_transport()

        if not semantic_model_file and not semantic_view:
            raise SnowflakeAPIError("Must provide either semantic_model_file or semantic_view")

        payload: dict[str, Any] = {"max_questions": max_questions}
        if semantic_model_file:
            payload["semantic_model_file"] = semantic_model_file
        elif semantic_view:
            payload["semantic_view"] = semantic_view

        result = await transport.post("cortex/analyst/suggest-questions", payload)
        return result.get("questions", [])

    async def validate_semantic_model(
        self, semantic_model_file: str | None = None, semantic_view: str | None = None
    ) -> dict[str, Any]:
        """Validate a semantic model (async).

        Args:
            semantic_model_file: Path to semantic model file
            semantic_view: Name of semantic view

        Returns:
            Dict: Validation results
        """
        transport = self._ensure_transport()

        if not semantic_model_file and not semantic_view:
            raise SnowflakeAPIError("Must provide either semantic_model_file or semantic_view")

        payload: dict[str, Any] = {}
        if semantic_model_file:
            payload["semantic_model_file"] = semantic_model_file
        elif semantic_view:
            payload["semantic_view"] = semantic_view

        return await transport.post("cortex/analyst/validate", payload)
