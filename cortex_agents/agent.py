"""Snowflake Cortex Agent API Client.

This module provides a client for interacting with Snowflake's Cortex Agents API.
Handles authentication, agent management, runs, threads, feedback, and response parsing.
"""

import logging
from typing import Any

import httpx

from .base import BaseAgent
from .core import AgentEntity, AgentFeedback, AgentRun, AgentThreads
from .core._transport import SyncTransport
from .core.response import AgentResponse
from .core.run import AgentInlineConfig

logger: logging.Logger = logging.getLogger(__name__)


class CortexAgent(BaseAgent):
    """Client for Snowflake Cortex Agents.

    Provides a simple, ergonomic interface for managing agents, running agents
    with streaming support, managing conversation threads, collecting user
    feedback, and parsing responses.

    Examples:
        ```python
        # Use with context manager for automatic cleanup
        with CortexAgent(account_url="https://...", pat="token123") as client:
            # Create an agent
            client.create_agent(
                name="MY_AGENT",
                config={
                    "instructions": {"system": "You are helpful"},
                    "models": {"orchestration": "claude-sonnet-4-6"}
                },
                database="MY_DB",
                schema="MY_SCHEMA"
            )

            # Run the agent with streaming
            response = client.run(
                "What's the revenue?",
                agent_name="MY_AGENT",
                database="MY_DB",
                schema="MY_SCHEMA"
            )

            # Stream events in real-time
            for event in response.stream():
                if event["type"] == "text.delta":
                    print(event["data"]["text"], end="", flush=True)

            # Or access complete results after streaming
            print(response.text)
            print(response.sql)

            # Submit feedback
            client.submit_feedback(
                agent_name="MY_AGENT",
                positive=True,
                orig_request_id=response.request_id,
                database="MY_DB",
                schema="MY_SCHEMA"
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
        """Initialize the Cortex Agent client.

        Args:
            account_url: Snowflake account URL. Defaults to SNOWFLAKE_ACCOUNT_URL
                environment variable.
            pat: Personal access token. Defaults to SNOWFLAKE_PAT environment
                variable.
            enable_logging: Enable request/response logging. Defaults to True.
            token_type: Authorization token type (e.g. ``"KEYPAIR_JWT"``).
        """
        super().__init__(account_url=account_url, pat=pat, enable_logging=enable_logging, token_type=token_type)

        self.session: httpx.Client = httpx.Client(
            headers=self._build_headers(),
            timeout=httpx.Timeout(connect=30.0, read=900.0, write=30.0, pool=30.0),
        )

        self._transport = SyncTransport(
            session=self.session,
            build_url=self._get_url,
            log_request=self._log_request,
            log_response=self._log_response,
            logger=logger,
        )

        self._entity = AgentEntity(self._transport)
        self._runner = AgentRun(self._transport)
        self._threads = AgentThreads(self._transport)
        self._feedback = AgentFeedback(self._transport)

        if enable_logging:
            logger.info("CortexAgent initialized")

    def __enter__(self) -> "CortexAgent":
        """Enter context manager.

        Returns:
            Self for context manager protocol.
        """
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and cleanup resources.

        Args:
            exc_type: Exception type (if any).
            exc_val: Exception value (if any).
            exc_tb: Exception traceback (if any).
        """
        self.close()

    def close(self) -> None:
        """Close the session and cleanup resources."""
        if self.session:
            self.session.close()
            logger.debug("CortexAgent session closed")

    # ===== Agent Management =====

    def create_agent(
        self,
        name: str,
        config: dict[str, Any],
        database: str,
        schema: str,
        create_mode: str | None = None,
    ) -> dict[str, Any]:
        """Create a Cortex Agent.

        Args:
            name: Agent name
            config: Agent configuration as dict (instructions, models, tools, etc.)
            database: Database name
            schema: Schema name
            create_mode: Optional creation mode

        Returns:
            Dict: Response with status

        Examples:
        ```python
        client.create_agent(
            name="MY_AGENT",
            config={
                "comment": "My helpful agent",
                "instructions": {
                    "system": "You are a helpful assistant",
                    "response": "Be concise"
                },
                "models": {"orchestration": "claude-sonnet-4-6"},
                "tools": [{
                    "tool_spec": {
                        "type": "cortex_analyst_text2sql",
                        "name": "analyst"
                    }
                }],
                "tool_resources": {
                    "analyst": {
                        "semantic_view": "DB.SCHEMA.VIEW",
                        "execution_environment": {
                            "type": "warehouse",
                            "warehouse": "MY_WH"
                        }
                    }
                }
            },
            database="MY_DB",
            schema="MY_SCHEMA"
        )
        ```
        """
        return self._entity.create_agent(
            name=name,
            config=config,
            database=database,
            schema=schema,
            create_mode=create_mode,
        )

    def get_agent(self, name: str, database: str, schema: str) -> dict[str, Any]:
        """Get agent details.

        Args:
            name: Agent name
            database: Database name
            schema: Schema name

        Returns:
            Dict: Agent configuration and metadata
        """
        return self._entity.get_agent(name=name, database=database, schema=schema)

    def update_agent(self, name: str, config: dict[str, Any], database: str, schema: str) -> dict[str, Any]:
        """Update an existing agent.

        Args:
            name: Agent name
            config: Updated configuration (partial updates allowed)
            database: Database name
            schema: Schema name

        Returns:
            Dict: Response with status
        """
        return self._entity.update_agent(name=name, config=config, database=database, schema=schema)

    def list_agents(
        self,
        database: str,
        schema: str,
        like: str | None = None,
        from_name: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """List agents in a schema.

        Args:
            database: Database name
            schema: Schema name
            like: Filter pattern (SQL wildcards)
            from_name: Start listing after this name
            limit: Maximum number to return (1-10000)

        Returns:
            list[Dict]: List of agent metadata
        """
        return self._entity.list_agents(
            database=database,
            schema=schema,
            like=like,
            from_name=from_name,
            limit=limit,
        )

    def delete_agent(self, name: str, database: str, schema: str, if_exists: bool = False) -> dict[str, Any]:
        """Delete an agent.

        Args:
            name: Agent name
            database: Database name
            schema: Schema name
            if_exists: Don't error if agent doesn't exist

        Returns:
            Dict: Response with status
        """
        return self._entity.delete_agent(
            name=name,
            database=database,
            schema=schema,
            if_exists=if_exists,
        )

    # ===== Agent Execution =====

    def run(
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
        """Run an agent with a query.

        This is a unified method that works both with saved agents and inline configuration.
        Always returns a streaming response (SSE events).

        Args:
            query: The user's current question. Optional when `messages`
                already contains the final user message.
            agent_name: Name of saved agent. Required if using a saved agent.
            database: Database name. Required if agent_name is provided.
            schema: Schema name. Required if agent_name is provided.
            thread_id: Thread identifier for conversation continuity.
            parent_message_id: Parent message ID. Required if thread_id is set.
            tool_choice: Controls tool selection strategy. Can be:
                - `{"type": "auto"}`: Automatic selection (default).
                - `{"type": "required"}`: At least one tool must be used.
                - `{"type": "tool", "name": ["tool1", "tool2"]}`: Specific tools only.
            messages: Conversation history to continue from. When provided, the
                latest user question from `query` is appended automatically.
                If `query` is omitted, `messages` must already end with a user
                message that follows the Run API schema.
            agent_config: Inline agent configuration for ephemeral runs.
                Only used if `agent_name` is None. Accepts keys:
                ``models``, ``instructions``, ``orchestration``, ``tools``,
                ``tool_resources``, ``tool_choice``.

        Returns:
            A response object with streaming events.
            - Use `response.stream()` to iterate through events.
            - Use `response.text`, `response.sql` for final results.

        Examples:
        ```python
        # Stream events in real-time with a saved agent
        with CortexAgent(account_url="...", pat="...") as client:
            response = client.run(
                "What's the revenue?",
                agent_name="MY_AGENT",
                database="SALES_DB",
                schema="ANALYTICS"
            )

            # Stream events
            for event in response.stream():
                if event["type"] == "text.delta":
                    print(event["data"]["text"], end="", flush=True)

            # Access complete results after streaming
            print(response.text)
            print(response.sql)

        # With tool choice constraints
        response = client.run(
            "Analyze this",
            agent_name="MY_AGENT",
            database="DB",
            schema="SCHEMA",
            tool_choice={"type": "required"}  # Require at least one tool
        )

        # Use only specific tools
        response = client.run(
            "Check inventory",
            agent_name="MY_AGENT",
            database="DB",
            schema="SCHEMA",
            tool_choice={
                "type": "tool",
                "name": ["analyst_tool", "search_tool"]
            }
        )

        # Inline agent config (no database/schema needed)
        response = client.run(
            "What's the revenue?",
            agent_config={
                "models": {"orchestration": "claude-sonnet-4-6"},
                "instructions": {"system": "You are helpful"},
                "tools": [...],
                "tool_resources": {...},
            }
        )

        # In a conversation thread
        response = client.run(
            "Continue analysis",
            agent_name="MY_AGENT",
            database="DB",
            schema="SCHEMA",
            thread_id=thread_id,
            parent_message_id=last_message_id
        )
        ```
        """
        return self._runner.run(
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

    def create_thread(self, origin_app: str | None = None) -> dict[str, Any]:
        """Create a conversation thread.

        Args:
            origin_app: Optional application identifier (max 16 bytes).
                Example: "my_app" or "sales_bot"

        Returns:
            Dictionary containing thread metadata including thread_id, thread_name,
            origin_application, created_on (datetime), and updated_on (datetime).

        Raises:
            ValueError: If origin_app exceeds 16 bytes.

        Examples:
            ```python
            thread = client.create_thread(origin_app="my_app")
            thread_id = thread["thread_id"]
            created = thread["created_on"]  # datetime object
            ```
        """
        return self._threads.create_thread(origin_app=origin_app)

    def get_thread(
        self,
        thread_id: str | int,
        limit: int = 20,
        last_message_id: int | None = None,
    ) -> dict[str, Any]:
        """Get thread details and messages.

        Args:
            thread_id: Thread ID
            limit: Number of messages to return (max 100)
            last_message_id: Last message ID for pagination

        Returns:
            Dict: Contains "metadata" and "messages" arrays
        """
        return self._threads.get_thread(
            thread_id=thread_id,
            limit=limit,
            last_message_id=last_message_id,
        )

    def update_thread(self, thread_id: str | int, name: str) -> dict[str, Any]:
        """Update thread name.

        Args:
            thread_id: Thread ID
            name: New thread name

        Returns:
            Dict: Response with status
        """
        return self._threads.update_thread(thread_id=thread_id, name=name)

    def list_threads(self, origin_app: str | None = None) -> list[dict[str, Any]]:
        """List all threads.

        Args:
            origin_app: Filter by application name

        Returns:
            List of thread dictionaries, each containing thread_id, thread_name,
            origin_application, created_on (datetime), and updated_on (datetime).

        Examples:
            ```python
            threads = client.list_threads(origin_app="my_app")
            for thread in threads:
                print(f"{thread['thread_id']}: {thread['thread_name']}")
                print(f"Created: {thread['created_on']}")
            ```
        """
        return self._threads.list_threads(origin_app=origin_app)

    def delete_thread(self, thread_id: str | int) -> dict[str, Any]:
        """Delete a thread and all its messages.

        Args:
            thread_id: Thread ID

        Returns:
            Dict: Success response
        """
        return self._threads.delete_thread(thread_id=thread_id)

    # ===== Feedback Methods =====

    def submit_feedback(
        self,
        agent_name: str,
        database: str,
        schema: str,
        positive: bool,
        feedback_message: str | None = None,
        categories: list[str] | None = None,
        orig_request_id: str | None = None,
        thread_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Submit feedback about an agent or a specific agent response.

        Can submit feedback at two levels:
        - Agent-level: General feedback about the agent (don't provide orig_request_id)
        - Request-level: Feedback about a specific response (provide orig_request_id)

        Args:
            agent_name: Name of the agent
            database: Database name
            schema: Schema name
            positive: Whether the feedback is positive (True) or negative (False)
            feedback_message: Optional detailed feedback message
            categories: Optional list of feedback categories (e.g., ["Something worked well"])
            orig_request_id: Optional request ID from response.request_id for request-level feedback
            thread_id: Optional thread ID if feedback is for a threaded conversation

        Returns:
            Dict: Confirmation response

        Examples:
        ```python
        # Agent-level feedback
        client.submit_feedback(
            agent_name="MY_AGENT",
            database="DB",
            schema="SCHEMA",
            positive=True,
            feedback_message="Great agent!",
            categories=["Something worked well"]
        )

        # Request-level feedback
        response = client.run("query", agent_name="MY_AGENT", database="DB", schema="SCHEMA")
        client.submit_feedback(
            agent_name="MY_AGENT",
            database="DB",
            schema="SCHEMA",
            positive=True,
            orig_request_id=response.request_id,
            feedback_message="Perfect answer!"
        )
        ```
        """
        return self._feedback.submit_feedback(
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

    def list_models(self) -> dict[str, Any]:
        """List available Cortex models.

        Returns:
            Dict: Available models and their configurations
        """
        return self._transport.get("cortex/models")
