"""Snowflake Cortex Analyst API Client.
https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/rest-api

This module provides a client for interacting with Snowflake's Cortex Analyst API.
Handles SQL generation from natural language using semantic models.
"""

import logging
from copy import deepcopy
from typing import Any

import httpx

from ._analyst_messages import normalize_analyst_messages
from ._analyst_response import AnalystResponse
from .base import BaseAgent, SnowflakeAPIError
from .core._transport import SyncTransport

logger: logging.Logger = logging.getLogger(__name__)


class CortexAnalyst(BaseAgent):
    """Client for Snowflake Cortex Analyst.

    Provides a simple interface for generating SQL from natural language questions
    using semantic models or semantic views. Supports multi-turn conversations,
    streaming responses, and user feedback submission.

    Examples:
        ```python
        from cortex_agents import CortexAnalyst

        # Use with context manager for automatic cleanup
        with CortexAnalyst() as analyst:
            response = analyst.message(
                "Which company had the most revenue?",
                semantic_model_file="@my_stage/model.yaml"
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
        """Initialize the Cortex Analyst client."""
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
        if enable_logging:
            logger.info("CortexAnalyst initialized")

    def __enter__(self) -> "CortexAnalyst":
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
            logger.debug("CortexAnalyst session closed")

    # ===== Analyst Message Methods =====

    def message(
        self,
        question: str,
        semantic_model_file: str | None = None,
        semantic_model: str | None = None,
        semantic_view: str | None = None,
        semantic_models: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
        stream: bool = True,
    ) -> AnalystResponse:
        """
        Send a message to Cortex Analyst to generate SQL from natural language.

        You must specify ONE of: semantic_model_file, semantic_model, semantic_view, or semantic_models.

        Args:
            question: The natural language question (str)
            semantic_model_file: Path to semantic model YAML file on stage
                                 (e.g., "@my_db.my_schema.my_stage/model.yaml")
            semantic_model: Full semantic model YAML as string
            semantic_view: Fully qualified semantic view name
                          (e.g., "MY_DB.MY_SCHEMA.MY_VIEW")
            semantic_models: List of semantic model/view dicts for multi-model selection
                            (e.g., [{"semantic_view": "DB.SCH.VIEW1"}, {"semantic_model_file": "@stage/model.yaml"}])
            messages: Full messages array for multi-turn conversations
                     (if not provided, will be built from question)

        Returns:
            AnalystResponse: Response object with SQL, text, and streaming support

        Examples:
            ```python
            # With semantic model file
            response = analyst.message(
                "Which company had most revenue?",
                semantic_model_file="@my_stage/model.yaml"
            )

            # Multi-turn conversation
            response1 = analyst.message(
                "What's total revenue?",
                semantic_model_file="@stage/model.yaml"
            )
            response2 = analyst.message(
                "How does that compare to last year?",
                semantic_model_file="@stage/model.yaml",
                messages=response1.conversation_messages
            )
            ```
        """
        if not isinstance(question, str):
            raise SnowflakeAPIError("question must be a string")

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

        model_flags = [bool(semantic_model_file), bool(semantic_model), bool(semantic_view), bool(semantic_models)]
        if sum(model_flags) != 1:
            raise SnowflakeAPIError(
                "You must provide exactly one of semantic_model_file, semantic_model, semantic_view, or semantic_models"
            )

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

        response_payload = self._transport.post("cortex/analyst/message", payload, stream=stream)
        return AnalystResponse(response_payload, stream=stream, request_messages=payload_messages)

    # ===== Feedback Methods =====

    def submit_feedback(self, request_id: str, positive: bool, feedback_message: str | None = None) -> dict[str, Any]:
        """Submit feedback about an Analyst response.

        Args:
            request_id: The request ID from response.request_id.
            positive: Whether the feedback is positive (True) or negative (False).
            feedback_message: Optional detailed feedback message.

        Returns:
            Confirmation response (typically empty dict on success).

        Examples:
            ```python
            analyst.submit_feedback(
                request_id=response.request_id,
                positive=True,
                feedback_message="Perfect SQL generation!"
            )
            ```
        """
        payload: dict[str, Any] = {"request_id": request_id, "positive": positive}
        if feedback_message:
            payload["feedback_message"] = feedback_message
        return self._transport.post("cortex/analyst/feedback", payload)

    def suggest_questions(
        self,
        semantic_model_file: str | None = None,
        semantic_view: str | None = None,
        max_questions: int = 3,
    ) -> list[str]:
        """Get suggested questions based on semantic model.

        Args:
            semantic_model_file: Path to semantic model file
            semantic_view: Name of semantic view
            max_questions: Maximum number of questions to return

        Returns:
            list[str]: Suggested questions
        """
        if not semantic_model_file and not semantic_view:
            raise SnowflakeAPIError("Must provide either semantic_model_file or semantic_view")

        payload: dict[str, Any] = {"max_questions": max_questions}
        if semantic_model_file:
            payload["semantic_model_file"] = semantic_model_file
        elif semantic_view:
            payload["semantic_view"] = semantic_view

        result = self._transport.post("cortex/analyst/suggest-questions", payload)
        return result.get("questions", [])

    def validate_semantic_model(
        self, semantic_model_file: str | None = None, semantic_view: str | None = None
    ) -> dict[str, Any]:
        """Validate a semantic model.

        Args:
            semantic_model_file: Path to semantic model file
            semantic_view: Name of semantic view

        Returns:
            Dict: Validation results
        """
        if not semantic_model_file and not semantic_view:
            raise SnowflakeAPIError("Must provide either semantic_model_file or semantic_view")

        payload: dict[str, Any] = {}
        if semantic_model_file:
            payload["semantic_model_file"] = semantic_model_file
        elif semantic_view:
            payload["semantic_view"] = semantic_view

        return self._transport.post("cortex/analyst/validate", payload)
