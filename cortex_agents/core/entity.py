"""Agent entity lifecycle helpers."""

from __future__ import annotations

from typing import Any


class AgentEntity:
    """Manage Cortex Agent entities synchronously."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    def create_agent(
        self,
        name: str,
        config: dict[str, Any],
        database: str,
        schema: str,
        *,
        create_mode: str | None = None,
    ) -> dict[str, Any]:
        """Create a new Cortex Agent in Snowflake.

        Args:
            name: Agent name.
            config: Agent configuration including instructions, models, tools, etc.
            database: Database name where the agent will be created.
            schema: Schema name where the agent will be created.
            create_mode: Optional creation mode (e.g., 'or_replace').

        Returns:
            Response dictionary with creation status.

        Raises:
            SnowflakeAPIError: If the API request fails.
        """
        endpoint = f"databases/{database}/schemas/{schema}/agents"
        params = {"createMode": create_mode} if create_mode else None

        payload: dict[str, Any] = {"name": name, **config}
        return self._transport.post(endpoint, payload, params=params)

    def get_agent(self, name: str, database: str, schema: str) -> dict[str, Any]:
        """Retrieve details of an existing Cortex Agent.

        Args:
            name: Agent name.
            database: Database name.
            schema: Schema name.

        Returns:
            Agent configuration and metadata.

        Raises:
            SnowflakeAPIError: If the agent doesn't exist or request fails.
        """
        endpoint = f"databases/{database}/schemas/{schema}/agents/{name}"
        return self._transport.get(endpoint)

    def update_agent(self, name: str, config: dict[str, Any], database: str, schema: str) -> dict[str, Any]:
        """Update an existing Cortex Agent's configuration.

        Args:
            name: Agent name.
            config: Updated agent configuration.
            database: Database name.
            schema: Schema name.

        Returns:
            Response dictionary with update status.

        Raises:
            SnowflakeAPIError: If the agent doesn't exist or request fails.
        """
        endpoint = f"databases/{database}/schemas/{schema}/agents/{name}"
        return self._transport.put(endpoint, config)

    def list_agents(
        self,
        database: str,
        schema: str,
        *,
        like: str | None = None,
        from_name: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """List all Cortex Agents in a schema.

        Args:
            database: Database name.
            schema: Schema name.
            like: SQL LIKE pattern to filter agent names (optional).
            from_name: Starting agent name for pagination (optional).
            limit: Maximum number of agents to return (optional).

        Returns:
            List of agent metadata dictionaries.

        Raises:
            SnowflakeAPIError: If the request fails.
        """
        endpoint = f"databases/{database}/schemas/{schema}/agents"
        params: dict[str, Any] = {}
        if like:
            params["like"] = like
        if from_name:
            params["fromName"] = from_name
        if limit:
            params["showLimit"] = limit

        return self._transport.get(endpoint, params if params else None)

    def delete_agent(
        self,
        name: str,
        database: str,
        schema: str,
        *,
        if_exists: bool = False,
    ) -> dict[str, Any]:
        """Delete a Cortex Agent.

        Args:
            name: Agent name.
            database: Database name.
            schema: Schema name.
            if_exists: If True, don't raise error if agent doesn't exist.

        Returns:
            Response dictionary with deletion status.

        Raises:
            SnowflakeAPIError: If the agent doesn't exist (when if_exists=False)
                or request fails.
        """
        endpoint = f"databases/{database}/schemas/{schema}/agents/{name}"
        params = {"ifExists": "true"} if if_exists else None
        return self._transport.delete(endpoint, params)


class AsyncAgentEntity:
    """Manage Cortex Agent entities asynchronously."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def create_agent(
        self,
        name: str,
        config: dict[str, Any],
        database: str,
        schema: str,
        *,
        create_mode: str | None = None,
    ) -> dict[str, Any]:
        """Create a new Cortex Agent in Snowflake (async).

        Args:
            name: Agent name.
            config: Agent configuration including instructions, models, tools, etc.
            database: Database name where the agent will be created.
            schema: Schema name where the agent will be created.
            create_mode: Optional creation mode (e.g., 'or_replace').

        Returns:
            Response dictionary with creation status.

        Raises:
            SnowflakeAPIError: If the API request fails.
        """
        endpoint = f"databases/{database}/schemas/{schema}/agents"
        params = {"createMode": create_mode} if create_mode else None

        payload: dict[str, Any] = {"name": name, **config}
        return await self._transport.post(endpoint, payload, params=params)

    async def get_agent(self, name: str, database: str, schema: str) -> dict[str, Any]:
        """Retrieve details of an existing Cortex Agent (async).

        Args:
            name: Agent name.
            database: Database name.
            schema: Schema name.

        Returns:
            Agent configuration and metadata.

        Raises:
            SnowflakeAPIError: If the agent doesn't exist or request fails.
        """
        endpoint = f"databases/{database}/schemas/{schema}/agents/{name}"
        return await self._transport.get(endpoint)

    async def update_agent(
        self,
        name: str,
        config: dict[str, Any],
        database: str,
        schema: str,
    ) -> dict[str, Any]:
        """Update an existing Cortex Agent's configuration (async).

        Args:
            name: Agent name.
            config: Updated agent configuration.
            database: Database name.
            schema: Schema name.

        Returns:
            Response dictionary with update status.

        Raises:
            SnowflakeAPIError: If the agent doesn't exist or request fails.
        """
        endpoint = f"databases/{database}/schemas/{schema}/agents/{name}"
        return await self._transport.put(endpoint, config)

    async def list_agents(
        self,
        database: str,
        schema: str,
        *,
        like: str | None = None,
        from_name: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """List all Cortex Agents in a schema (async).

        Args:
            database: Database name.
            schema: Schema name.
            like: SQL LIKE pattern to filter agent names (optional).
            from_name: Starting agent name for pagination (optional).
            limit: Maximum number of agents to return (optional).

        Returns:
            List of agent metadata dictionaries.

        Raises:
            SnowflakeAPIError: If the request fails.
        """
        endpoint = f"databases/{database}/schemas/{schema}/agents"
        params: dict[str, Any] = {}
        if like:
            params["like"] = like
        if from_name:
            params["fromName"] = from_name
        if limit:
            params["showLimit"] = limit

        return await self._transport.get(endpoint, params if params else None)

    async def delete_agent(
        self,
        name: str,
        database: str,
        schema: str,
        *,
        if_exists: bool = False,
    ) -> dict[str, Any]:
        """Delete a Cortex Agent (async).

        Args:
            name: Agent name.
            database: Database name.
            schema: Schema name.
            if_exists: If True, don't raise error if agent doesn't exist.

        Returns:
            Response dictionary with deletion status.

        Raises:
            SnowflakeAPIError: If the agent doesn't exist (when if_exists=False)
                or request fails.
        """
        endpoint = f"databases/{database}/schemas/{schema}/agents/{name}"
        params = {"ifExists": "true"} if if_exists else None
        return await self._transport.delete(endpoint, params)
