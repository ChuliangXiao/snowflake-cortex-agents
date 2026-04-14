"""Async Snowflake Cortex Agent API Client.

This module provides an async client for interacting with Snowflake's Cortex Agents API.
Handles authentication, agent management, runs, threads, feedback, and response parsing.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .base import BaseAgent, SnowflakeAPIError
from .core import AsyncAgentEntity, AsyncAgentFeedback, AsyncAgentRun, AsyncAgentThreads
from .core._transport import AsyncTransport
from .core.response import AgentResponse
from .core.run import AgentInlineConfig

logger: logging.Logger = logging.getLogger(__name__)


class AsyncCortexAgent(BaseAgent):
    """Async client for Snowflake Cortex Agents.

    Exposes ergonomic helpers for managing agents, executing runs with
    streaming responses, orchestrating conversation threads, and collecting
    feedback. Use the async context manager for automatic resource management.

    Examples:
    ```python
    # Use with async context manager for automatic cleanup
    async with AsyncCortexAgent(account_url="https://...", pat="token123") as client:
        # Create an agent
        await client.create_agent(
            name="MY_AGENT",
            config={
                "instructions": {"system": "You are helpful"},
                "models": {"orchestration": "claude-sonnet-4-6"}
            },
            database="MY_DB",
            schema="MY_SCHEMA"
        )

        # Run the agent
        response = await client.run(
            "What's the revenue?",
            agent_name="MY_AGENT",
            database="MY_DB",
            schema="MY_SCHEMA"
        )

        # Stream results
        async for event in response.astream():
            if event['type'] == 'text.delta':
                print(event['data']['text'], end='', flush=True)

        # Submit feedback
        await client.submit_feedback(
            agent_name="MY_AGENT",
            database="MY_DB",
            schema="MY_SCHEMA",
            positive=True,
            orig_request_id=response.request_id
        )
    ```
    """

    def __init__(
        self,
        account_url: str | None = None,
        pat: str | None = None,
        enable_logging: bool = True,
        token_type: str | None = None,
    ) -> None:
        """Initialize the async Cortex agent facade and lazy managers.

        Args:
            account_url: Optional Snowflake account URL; falls back to environment variable.
            pat: Optional personal access token; falls back to environment variable.
            enable_logging: Whether to emit debug log entries for HTTP activity.
            token_type: Authorization token type (e.g. ``"KEYPAIR_JWT"``).
        """
        super().__init__(account_url=account_url, pat=pat, enable_logging=enable_logging, token_type=token_type)

        self._client: httpx.AsyncClient | None = None
        self._transport: AsyncTransport | None = None
        self._entity: AsyncAgentEntity | None = None
        self._runner: AsyncAgentRun | None = None
        self._threads: AsyncAgentThreads | None = None
        self._feedback: AsyncAgentFeedback | None = None

        if enable_logging:
            logger.info("AsyncCortexAgent initialized")

    async def __aenter__(self) -> AsyncCortexAgent:
        """Create the underlying httpx client and wire up core managers."""
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
        self._entity = AsyncAgentEntity(self._transport)
        self._runner = AsyncAgentRun(self._transport)
        self._threads = AsyncAgentThreads(self._transport)
        self._feedback = AsyncAgentFeedback(self._transport)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Shutdown resources when exiting an async context manager block."""
        await self.aclose()

    def close(self) -> None:
        """Synchronously close resources for compatibility with BaseAgent."""
        if not self._client:
            return

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.aclose())
        else:
            raise SnowflakeAPIError("close() cannot run while the event loop is active; use 'await aclose()' instead")

    async def aclose(self) -> None:
        """Close the httpx client and drop cached managers for reuse."""
        if self._client:
            await self._client.aclose()
            logger.debug("AsyncCortexAgent client closed")

        self._client = None
        self._transport = None
        self._entity = None
        self._runner = None
        self._threads = None
        self._feedback = None

    def _ensure_transport(self) -> AsyncTransport:
        """Return the transport instance or raise if the client is not initialized."""
        if not self._transport:
            raise SnowflakeAPIError("Client not initialized. Use async with context manager.")
        return self._transport

    def _ensure_entity_manager(self) -> AsyncAgentEntity:
        """Instantiate or return the cached agent entity manager."""
        transport = self._ensure_transport()
        if self._entity is None:
            self._entity = AsyncAgentEntity(transport)
        return self._entity

    def _ensure_run_manager(self) -> AsyncAgentRun:
        """Instantiate or return the cached run execution manager."""
        transport = self._ensure_transport()
        if self._runner is None:
            self._runner = AsyncAgentRun(transport)
        return self._runner

    def _ensure_threads_manager(self) -> AsyncAgentThreads:
        """Instantiate or return the cached conversation threads manager."""
        transport = self._ensure_transport()
        if self._threads is None:
            self._threads = AsyncAgentThreads(transport)
        return self._threads

    def _ensure_feedback_manager(self) -> AsyncAgentFeedback:
        """Instantiate or return the cached feedback submission manager."""
        transport = self._ensure_transport()
        if self._feedback is None:
            self._feedback = AsyncAgentFeedback(transport)
        return self._feedback

    # ===== Agent Management =====

    async def create_agent(
        self,
        name: str,
        config: dict[str, Any],
        database: str,
        schema: str,
        create_mode: str | None = None,
    ) -> dict[str, Any]:
        """Create a Cortex agent with the provided configuration.

        Args:
            name: Logical name for the agent within the schema.
            config: Configuration payload including instructions, models, tools, etc.
            database: Target database for the agent.
            schema: Target schema for the agent.
            create_mode: Optional behaviour flag (for example, "CREATE OR REPLACE").

        Returns:
            dict[str, Any]: Raw Snowflake API response describing the new agent.
        """
        entity = self._ensure_entity_manager()
        return await entity.create_agent(
            name=name,
            config=config,
            database=database,
            schema=schema,
            create_mode=create_mode,
        )

    async def get_agent(self, name: str, database: str, schema: str) -> dict[str, Any]:
        """Retrieve a single agent's metadata.

        Args:
            name: Agent name to fetch.
            database: Database containing the agent.
            schema: Schema containing the agent.

        Returns:
            dict[str, Any]: Agent definition and metadata.
        """
        entity = self._ensure_entity_manager()
        return await entity.get_agent(name=name, database=database, schema=schema)

    async def update_agent(
        self,
        name: str,
        config: dict[str, Any],
        database: str,
        schema: str,
    ) -> dict[str, Any]:
        """Update an existing agent with a partial or full configuration payload.

        Args:
            name: Agent name to modify.
            config: Partial or full configuration update.
            database: Database containing the agent.
            schema: Schema containing the agent.

        Returns:
            dict[str, Any]: Raw Snowflake API response for the update request.
        """
        entity = self._ensure_entity_manager()
        return await entity.update_agent(name=name, config=config, database=database, schema=schema)

    async def list_agents(
        self,
        database: str,
        schema: str,
        like: str | None = None,
        from_name: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """List agents in the specified schema with optional pagination and filters.

        Args:
            database: Database containing the agents.
            schema: Schema containing the agents.
            like: Optional SQL-style filter pattern.
            from_name: Continue listing after this agent name.
            limit: Maximum number of results to return.

        Returns:
            list[dict[str, Any]]: Collection of agent metadata dictionaries.
        """
        entity = self._ensure_entity_manager()
        return await entity.list_agents(
            database=database,
            schema=schema,
            like=like,
            from_name=from_name,
            limit=limit,
        )

    async def delete_agent(
        self,
        name: str,
        database: str,
        schema: str,
        if_exists: bool = False,
    ) -> dict[str, Any]:
        """Delete a Cortex agent, optionally ignoring missing agents.

        Args:
            name: Agent name to delete.
            database: Database containing the agent.
            schema: Schema containing the agent.
            if_exists: Do not raise an error when the agent is absent.

        Returns:
            dict[str, Any]: API response confirming the operation.
        """
        entity = self._ensure_entity_manager()
        return await entity.delete_agent(
            name=name,
            database=database,
            schema=schema,
            if_exists=if_exists,
        )

    # ===== Agent Execution =====

    async def run(
        self,
        query: str | None = None,
        agent_name: str | None = None,
        database: str | None = None,
        schema: str | None = None,
        thread_id: str | int | None = None,
        parent_message_id: str | int | None = None,
        tool_choice: dict[str, Any] | None = None,
        messages: list[dict[str, Any]] | None = None,
        stream: bool = True,
        agent_config: AgentInlineConfig | None = None,
    ) -> AgentResponse:
        """Execute an agent run and return an async response wrapper.

        The method supports saved agents, inline configurations, and conversational
        context via threads. The returned ``AgentResponse`` exposes streaming
        helpers for consuming Server-Sent Events (SSE) asynchronously.

        Args:
            query: User question to send to the agent.
            agent_name: Saved agent name (required when ``database``/``schema`` are provided).
            database: Database containing the saved agent.
            schema: Schema containing the saved agent.
            thread_id: Optional conversation thread identifier.
            parent_message_id: Optional parent message id used with threads.
            tool_choice: Tool execution strategy override.
            messages: Conversation history to include in the request payload.
            agent_config: Inline configuration for ad-hoc runs.

        Returns:
            AgentResponse: Wrapper offering async iteration over streaming events.
        Examples:
        ```python
        async with AsyncCortexAgent(account_url="...", pat="...") as client:
            # With saved agent
            response = await client.run(
                "What's the revenue?",
                agent_name="MY_AGENT",
                database="SALES_DB",
                schema="ANALYTICS"
            )

            # Stream results
            async for event in response.astream():
                if event['type'] == 'text.delta':
                    print(event['data']['text'], end='', flush=True)
        ```
        """
        runner = self._ensure_run_manager()
        return await runner.run(
            query=query,
            agent_name=agent_name,
            database=database,
            schema=schema,
            thread_id=thread_id,
            parent_message_id=parent_message_id,
            tool_choice=tool_choice,
            messages=messages,
            agent_config=agent_config,
            stream=stream,
        )

    # ===== Thread Management =====

    async def create_thread(self, origin_app: str | None = None) -> dict[str, Any]:
        """Create a new Cortex conversation thread.

        Args:
            origin_app: Optional application identifier (max 16 bytes).
                Example: "my_app" or "sales_bot"

        Returns:
            dict[str, Any]: Thread metadata including the thread identifier.

        Raises:
            ValueError: If origin_app exceeds 16 bytes.
        """
        threads = self._ensure_threads_manager()
        return await threads.create_thread(origin_app=origin_app)

    async def get_thread(
        self,
        thread_id: str | int,
        *,
        limit: int = 20,
        last_message_id: int | None = None,
    ) -> dict[str, Any]:
        """Fetch thread metadata and messages with optional pagination.

        Args:
            thread_id: Thread identifier to fetch.
            limit: Number of messages to return (max 100).
            last_message_id: Continue listing messages after this id.

        Returns:
            dict[str, Any]: Metadata and message history for the thread.
        """
        threads = self._ensure_threads_manager()
        return await threads.get_thread(
            thread_id=thread_id,
            limit=limit,
            last_message_id=last_message_id,
        )

    async def update_thread(self, thread_id: str | int, name: str) -> dict[str, Any]:
        """Rename an existing conversation thread.

        Args:
            thread_id: Identifier for the thread to update.
            name: New display name for the thread.

        Returns:
            dict[str, Any]: API response describing the updated thread.
        """
        threads = self._ensure_threads_manager()
        return await threads.update_thread(thread_id=thread_id, name=name)

    async def list_threads(self, origin_app: str | None = None) -> list[dict[str, Any]]:
        """List available threads, optionally filtered by origin application.

        Args:
            origin_app: Optional application identifier to filter the results.

        Returns:
            list[dict[str, Any]]: Collection of thread metadata entries.
        """
        threads = self._ensure_threads_manager()
        return await threads.list_threads(origin_app=origin_app)

    async def delete_thread(self, thread_id: str | int) -> dict[str, Any]:
        """Delete a conversation thread and its messages.

        Args:
            thread_id: Identifier for the thread to remove.

        Returns:
            dict[str, Any]: API response confirming deletion.
        """
        threads = self._ensure_threads_manager()
        return await threads.delete_thread(thread_id=thread_id)

    # ===== Feedback Methods =====

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
        """Submit feedback about an agent response or interaction.

        Args:
            agent_name: Agent associated with the feedback entry.
            database: Database containing the agent.
            schema: Schema containing the agent.
            positive: Indicates positive (True) or negative (False) feedback.
            feedback_message: Optional free-form feedback text.
            categories: Optional list of structured feedback categories.
            orig_request_id: Optional request identifier from a previous run.
            thread_id: Optional conversation thread to associate with feedback.

        Returns:
            dict[str, Any]: API acknowledgement payload.
        """
        feedback = self._ensure_feedback_manager()
        return await feedback.submit_feedback(
            agent_name=agent_name,
            database=database,
            schema=schema,
            positive=positive,
            feedback_message=feedback_message,
            categories=categories,
            orig_request_id=orig_request_id,
            thread_id=thread_id,
        )

    # ===== Utility Methods =====

    async def list_models(self) -> dict[str, Any]:
        """Return the list of Cortex models visible to the current account.

        Returns:
            dict[str, Any]: Mapping of available models and their attributes.
        """
        transport = self._ensure_transport()
        return await transport.get("cortex/models")
