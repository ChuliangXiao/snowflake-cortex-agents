"""Thread management helpers for Cortex Agents."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ._transport import AsyncTransport, SyncTransport


def _parse_timestamps(result: dict[str, Any]) -> dict[str, Any]:
    """Parse timestamp fields from milliseconds to datetime objects.

    Args:
        result: Dictionary potentially containing created_on and updated_on timestamps.

    Returns:
        The same dictionary with timestamps converted to datetime objects.
    """
    if "created_on" in result and isinstance(result["created_on"], (int, float)):
        result["created_on"] = datetime.fromtimestamp(result["created_on"] / 1000, tz=timezone.utc)
    if "updated_on" in result and isinstance(result["updated_on"], (int, float)):
        result["updated_on"] = datetime.fromtimestamp(result["updated_on"] / 1000, tz=timezone.utc)
    return result


def _build_create_thread_payload(origin_app: str | None) -> dict[str, Any]:
    """Build payload for create_thread request.

    Args:
        origin_app: Optional application name for tracking thread origin (max 16 bytes).

    Returns:
        Payload dictionary for the API request.

    Raises:
        ValueError: If origin_app exceeds 16 bytes.
    """
    payload: dict[str, Any] = {}
    if origin_app:
        # Validate byte length (Snowflake API limit is 16 bytes)
        byte_length = len(origin_app.encode("utf-8"))
        if byte_length > 16:
            raise ValueError(
                f"origin_app exceeds maximum length of 16 bytes. "
                f"'{origin_app}' is {byte_length} bytes. "
                f"Please use a shorter application name."
            )
        payload["origin_application"] = origin_app
    return payload


class AgentThreads:
    """Thread operations for the synchronous Cortex Agent client."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def create_thread(self, origin_app: str | None = None) -> dict[str, Any]:
        """Create a new conversation thread.

        Args:
            origin_app: Optional application name for tracking thread origin (max 16 bytes).

        Returns:
            Dictionary containing thread metadata including thread_id, thread_name,
            origin_application, created_on, and updated_on.

        Raises:
            ValueError: If origin_app exceeds 16 bytes.
            SnowflakeAPIError: If the request fails.

        Examples:
            ```python
            thread = client.create_thread(origin_app="my_app")
            thread_id = thread["thread_id"]
            ```
        """
        payload = _build_create_thread_payload(origin_app)
        result = self._transport.post("cortex/threads", payload)
        # Guard: some API versions return a plain string UUID
        if isinstance(result, str):
            return {"thread_id": result}
        return _parse_timestamps(result)

    def get_thread(
        self,
        thread_id: str | int,
        *,
        limit: int = 20,
        last_message_id: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve a conversation thread with its messages.

        Args:
            thread_id: Thread ID to retrieve.
            limit: Maximum number of messages to return (default: 20).
            last_message_id: Message ID to start pagination from (optional).

        Returns:
            Dictionary containing thread metadata and messages.

        Raises:
            SnowflakeAPIError: If the thread doesn't exist or request fails.

        Examples:
            ```python
            thread = client.get_thread(thread_id, limit=50)
            for msg in thread['messages']:
                print(msg['content'])
            ```
        """
        endpoint = f"cortex/threads/{thread_id}"
        params: dict[str, Any] = {"page_size": limit}
        if last_message_id is not None:
            params["last_message_id"] = last_message_id

        return self._transport.get(endpoint, params)

    def update_thread(self, thread_id: str | int, name: str) -> dict[str, Any]:
        """Update a thread's name.

        Args:
            thread_id: Thread ID to update.
            name: New thread name.

        Returns:
            Response dictionary with update status.

        Raises:
            SnowflakeAPIError: If the thread doesn't exist or request fails.

        Examples:
            ```python
            client.update_thread(thread_id, "Sales Analysis Chat")
            ```
        """
        endpoint = f"cortex/threads/{thread_id}"
        return self._transport.post(endpoint, {"thread_name": name})

    def list_threads(self, origin_app: str | None = None) -> list[dict[str, Any]]:
        """List all conversation threads.

        Args:
            origin_app: Filter by application name (optional).

        Returns:
            List of thread dictionaries, each containing thread_id, thread_name,
            origin_application, created_on, and updated_on.

        Raises:
            SnowflakeAPIError: If the request fails.

        Examples:
            ```python
            threads = client.list_threads(origin_app="my_app")
            for thread in threads:
                print(f"{thread['thread_id']}: {thread['thread_name']}")
            ```
        """
        params = {"origin_application": origin_app} if origin_app else None
        result = self._transport.get("cortex/threads", params)
        return [_parse_timestamps(thread) for thread in result]

    def delete_thread(self, thread_id: str | int) -> dict[str, Any]:
        """Delete a conversation thread.

        Args:
            thread_id: Thread ID to delete.

        Returns:
            Response dictionary with deletion status.

        Raises:
            SnowflakeAPIError: If the thread doesn't exist or request fails.

        Examples:
            ```python
            client.delete_thread(thread_id)
            ```
        """
        endpoint = f"cortex/threads/{thread_id}"
        return self._transport.delete(endpoint)


class AsyncAgentThreads:
    """Thread operations for the asynchronous Cortex Agent client."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def create_thread(self, origin_app: str | None = None) -> dict[str, Any]:
        """Create a new conversation thread (async).

        Args:
            origin_app: Optional application name for tracking thread origin (max 16 bytes).

        Returns:
            Dictionary containing thread metadata including thread_id, thread_name,
            origin_application, created_on, and updated_on.

        Raises:
            ValueError: If origin_app exceeds 16 bytes.
            SnowflakeAPIError: If the request fails.

        Examples:
            ```python
            thread = await client.create_thread(origin_app="my_app")
            thread_id = thread["thread_id"]
            ```
        """
        payload = _build_create_thread_payload(origin_app)
        result = await self._transport.post("cortex/threads", payload)
        # Guard: some API versions return a plain string UUID
        if isinstance(result, str):
            return {"thread_id": result}
        return _parse_timestamps(result)

    async def get_thread(
        self,
        thread_id: str | int,
        *,
        limit: int = 20,
        last_message_id: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve a conversation thread with its messages (async).

        Args:
            thread_id: Thread ID to retrieve.
            limit: Maximum number of messages to return (default: 20).
            last_message_id: Message ID to start pagination from (optional).

        Returns:
            Dictionary containing thread metadata and messages.

        Raises:
            SnowflakeAPIError: If the thread doesn't exist or request fails.

        Examples:
            ```python
            thread = await client.get_thread(thread_id, limit=50)
            for msg in thread['messages']:
                print(msg['content'])
            ```
        """
        endpoint = f"cortex/threads/{thread_id}"
        params: dict[str, Any] = {"page_size": limit}
        if last_message_id is not None:
            params["last_message_id"] = last_message_id

        return await self._transport.get(endpoint, params)

    async def update_thread(self, thread_id: str | int, name: str) -> dict[str, Any]:
        """Update a thread's name (async).

        Args:
            thread_id: Thread ID to update.
            name: New thread name.

        Returns:
            Response dictionary with update status.

        Raises:
            SnowflakeAPIError: If the thread doesn't exist or request fails.

        Examples:
            ```python
            await client.update_thread(thread_id, "Sales Analysis Chat")
            ```
        """
        endpoint = f"cortex/threads/{thread_id}"
        return await self._transport.post(endpoint, {"thread_name": name})

    async def list_threads(self, origin_app: str | None = None) -> list[dict[str, Any]]:
        """List all conversation threads (async).

        Args:
            origin_app: Filter by application name (optional).

        Returns:
            List of thread dictionaries, each containing thread_id, thread_name,
            origin_application, created_on, and updated_on.

        Raises:
            SnowflakeAPIError: If the request fails.

        Examples:
            ```python
            threads = await client.list_threads(origin_app="my_app")
            for thread in threads:
                print(f"{thread['thread_id']}: {thread['thread_name']}")
            ```
        """
        params = {"origin_application": origin_app} if origin_app else None
        result = await self._transport.get("cortex/threads", params)
        return [_parse_timestamps(thread) for thread in result]

    async def delete_thread(self, thread_id: str | int) -> dict[str, Any]:
        """Delete a conversation thread (async).

        Args:
            thread_id: Thread ID to delete.

        Returns:
            Response dictionary with deletion status.

        Raises:
            SnowflakeAPIError: If the thread doesn't exist or request fails.

        Examples:
            ```python
            await client.delete_thread(thread_id)
            ```
        """
        endpoint = f"cortex/threads/{thread_id}"
        return await self._transport.delete(endpoint)
