"""Tests for URL encoding in the centralized URL-building layer.

Verifies that BaseAgent._get_url() correctly percent-encodes path segments,
prevents double-encoding, and preserves :action suffixes.
"""

from __future__ import annotations

from unittest.mock import patch

from cortex_agents.base import BaseAgent

# ---------------------------------------------------------------------------
# Minimal concrete subclass for testing
# ---------------------------------------------------------------------------


class _ConcreteAgent(BaseAgent):
    """Minimal concrete subclass to expose _get_url for testing."""

    def close(self) -> None:
        pass


def _make_agent(account_url: str = "https://myaccount.snowflakecomputing.com") -> _ConcreteAgent:
    """Create a _ConcreteAgent with a fixed account_url and dummy PAT."""
    with patch("cortex_agents.base.load_credentials", return_value=(account_url, "dummy-pat")):
        return _ConcreteAgent(account_url=account_url, pat="dummy-pat")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE = "https://myaccount.snowflakecomputing.com/api/v2"


# ---------------------------------------------------------------------------
# Normal identifiers - no encoding needed
# ---------------------------------------------------------------------------


class TestNormalIdentifiers:
    """Normal identifiers (letters, digits, underscores) should be unchanged."""

    def test_simple_agent_path(self):
        agent = _make_agent()
        url = agent._get_url("databases/MY_DB/schemas/MY_SCHEMA/agents/MY_AGENT")
        assert url == f"{BASE}/databases/MY_DB/schemas/MY_SCHEMA/agents/MY_AGENT"

    def test_alphanumeric_segments_unchanged(self):
        agent = _make_agent()
        url = agent._get_url("databases/DB1/schemas/SC1/agents/AGENT1")
        assert url == f"{BASE}/databases/DB1/schemas/SC1/agents/AGENT1"

    def test_underscore_in_names(self):
        agent = _make_agent()
        url = agent._get_url("databases/MY_DB/schemas/MY_SCHEMA/agents/MY_AGENT")
        assert "MY_DB" in url
        assert "MY_SCHEMA" in url
        assert "MY_AGENT" in url

    def test_integer_like_segment_unchanged(self):
        agent = _make_agent()
        url = agent._get_url("cortex/threads/42")
        assert url == f"{BASE}/cortex/threads/42"

    def test_uuid_thread_id_unchanged(self):
        agent = _make_agent()
        thread_id = "550e8400-e29b-41d4-a716-446655440000"
        url = agent._get_url(f"cortex/threads/{thread_id}")
        assert thread_id in url


# ---------------------------------------------------------------------------
# Injection characters encoded
# ---------------------------------------------------------------------------


class TestSpecialCharactersEncoded:
    """Special characters in path segments must be percent-encoded."""

    def test_space_encoded(self):
        agent = _make_agent()
        url = agent._get_url("databases/my db/schemas/my schema/agents/my agent")
        assert " " not in url
        assert "my%20db" in url
        assert "my%20schema" in url
        assert "my%20agent" in url

    def test_hash_in_segment_encoded(self):
        agent = _make_agent()
        # Pass the raw value (as call-sites now do) to check _get_url encodes it
        url = agent._get_url("databases/DB#1/schemas/SC/agents/A")
        assert "#" not in url
        assert "DB%231" in url

    def test_dollar_sign_encoded(self):
        agent = _make_agent()
        url = agent._get_url("databases/DB$1/schemas/SC/agents/A")
        assert "$" not in url
        assert "DB%241" in url

    def test_at_sign_encoded(self):
        agent = _make_agent()
        url = agent._get_url("databases/DB/schemas/SC/agents/ag@v1")
        assert "@" not in url
        assert "ag%40v1" in url

    def test_percent_in_input_is_encoded(self):
        """A literal % in a segment name should itself be encoded."""
        agent = _make_agent()
        url = agent._get_url("databases/DB/schemas/SC/agents/ag%name")
        assert "ag%25name" in url


# ---------------------------------------------------------------------------
# No double-encoding
# ---------------------------------------------------------------------------


class TestNoDoubleEncoding:
    """When raw values are passed, _get_url must not double-encode them."""

    def test_space_not_double_encoded(self):
        """Raw space in segment -> %20, never %2520."""
        agent = _make_agent()
        url = agent._get_url("databases/my db/schemas/SC/agents/A")
        assert "%2520" not in url
        assert "%20" in url

    def test_hash_not_double_encoded(self):
        """Raw # in segment -> %23, never %2523."""
        agent = _make_agent()
        url = agent._get_url("databases/DB#1/schemas/SC/agents/A")
        assert "%2523" not in url
        assert "%23" in url

    def test_normal_value_has_no_percent_sequences(self):
        """Completely safe identifiers produce no percent sequences."""
        agent = _make_agent()
        url = agent._get_url("databases/MYDB/schemas/MYSC/agents/MYAGENT")
        # Strip the https:// scheme before checking - the scheme uses //
        path_part = url.split("//", 1)[1]
        assert "%" not in path_part


# ---------------------------------------------------------------------------
# :action suffix handling
# ---------------------------------------------------------------------------


class TestActionSuffixHandling:
    """The :action suffix (e.g., :run, :feedback) must be preserved literally."""

    def test_run_suffix_preserved(self):
        agent = _make_agent()
        url = agent._get_url("databases/DB/schemas/SC/agents/MY_AGENT:run")
        assert url.endswith(":run")
        assert "%3A" not in url

    def test_feedback_suffix_preserved(self):
        agent = _make_agent()
        url = agent._get_url("databases/DB/schemas/SC/agents/MY_AGENT:feedback")
        assert url.endswith(":feedback")
        assert "%3A" not in url

    def test_action_suffix_with_space_in_agent_name(self):
        """Agent name before : should be encoded; action after : should be safe."""
        agent = _make_agent()
        url = agent._get_url("databases/DB/schemas/SC/agents/my agent:run")
        assert "my%20agent" in url
        assert url.endswith(":run")
        assert "%3A" not in url

    def test_inline_run_endpoint(self):
        """The fixed cortex/agent:run endpoint should be preserved as-is."""
        agent = _make_agent()
        url = agent._get_url("cortex/agent:run")
        assert url == f"{BASE}/cortex/agent:run"

    def test_normal_agent_run_endpoint(self):
        agent = _make_agent()
        url = agent._get_url("databases/MY_DB/schemas/MY_SCHEMA/agents/MY_AGENT:run")
        assert url == f"{BASE}/databases/MY_DB/schemas/MY_SCHEMA/agents/MY_AGENT:run"

    def test_normal_agent_feedback_endpoint(self):
        agent = _make_agent()
        url = agent._get_url("databases/MY_DB/schemas/MY_SCHEMA/agents/MY_AGENT:feedback")
        assert url == f"{BASE}/databases/MY_DB/schemas/MY_SCHEMA/agents/MY_AGENT:feedback"


# ---------------------------------------------------------------------------
# Full URL structure
# ---------------------------------------------------------------------------


class TestFullURLStructure:
    """Verify the full URL format including base URL prefix."""

    def test_url_starts_with_account_url(self):
        agent = _make_agent("https://xy12345.snowflakecomputing.com")
        url = agent._get_url("databases/DB/schemas/SC/agents/A")
        assert url.startswith("https://xy12345.snowflakecomputing.com/api/v2/")

    def test_url_contains_api_v2_prefix(self):
        agent = _make_agent()
        url = agent._get_url("databases/DB/schemas/SC/agents/A")
        assert "/api/v2/" in url

    def test_leading_slash_stripped(self):
        """_get_url should handle endpoints with or without a leading slash."""
        agent = _make_agent()
        url_no_slash = agent._get_url("databases/DB/schemas/SC/agents/A")
        url_with_slash = agent._get_url("/databases/DB/schemas/SC/agents/A")
        assert url_no_slash == url_with_slash


# ---------------------------------------------------------------------------
# Query-string mangling regression tests
# ---------------------------------------------------------------------------


class TestQueryStringNotAppendedToEndpoint:
    """Verify that query params (e.g. createMode) are NOT appended to the endpoint
    string passed to _get_url, because _get_url percent-encodes ? and = signs.
    """

    def test_get_url_mangles_query_string_in_path(self):
        """Demonstrate why appending ?createMode=... to the endpoint is wrong.

        _get_url encodes every segment including '?' and '=', so a query string
        baked into the endpoint path is mangled into the URL path rather than
        becoming a proper query parameter.
        """
        agent = _make_agent()
        url = agent._get_url("databases/DB/schemas/SC/agents?createMode=or_replace")
        # The '?' gets encoded as %3F and '=' as %3D — it's part of the path
        assert "%3F" in url or "%3D" in url, (
            "Expected _get_url to mangle the query string into the path; "
            "this confirms the bug that callers must NOT use this pattern"
        )
        # The mangled URL must NOT contain a real query-string separator
        assert "?" not in url

    def test_create_agent_endpoint_has_no_query_string(self):
        """AgentEntity.create_agent must pass the endpoint WITHOUT '?' appended.

        The createMode value should be delivered via the params kwarg to
        transport.post, not baked into the endpoint string.
        """
        from unittest.mock import MagicMock

        from cortex_agents.core.entity import AgentEntity

        mock_transport = MagicMock()
        mock_transport.post.return_value = {"status": "success"}

        entity = AgentEntity(mock_transport)
        entity.create_agent(
            name="MY_AGENT",
            config={"model": "llama3"},
            database="DB",
            schema="SC",
            create_mode="or_replace",
        )

        mock_transport.post.assert_called_once()
        call_args = mock_transport.post.call_args
        endpoint_used = call_args.args[0]

        # The endpoint must NOT contain a '?' — query params go via params kwarg
        assert "?" not in endpoint_used, (
            f"endpoint '{endpoint_used}' must not contain a query string; pass createMode via params kwarg instead"
        )
        # The createMode value must reach transport via the params kwarg
        assert call_args.kwargs.get("params") == {"createMode": "or_replace"}

    def test_create_agent_no_create_mode_passes_none_params(self):
        """When create_mode is not supplied, params kwarg should be None."""
        from unittest.mock import MagicMock

        from cortex_agents.core.entity import AgentEntity

        mock_transport = MagicMock()
        mock_transport.post.return_value = {"status": "success"}

        entity = AgentEntity(mock_transport)
        entity.create_agent(
            name="MY_AGENT",
            config={},
            database="DB",
            schema="SC",
        )

        call_args = mock_transport.post.call_args
        assert call_args.kwargs.get("params") is None

    def test_async_create_agent_endpoint_has_no_query_string(self):
        """AsyncAgentEntity.create_agent must also pass createMode via params."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from cortex_agents.core.entity import AsyncAgentEntity

        mock_transport = MagicMock()
        mock_transport.post = AsyncMock(return_value={"status": "success"})

        entity = AsyncAgentEntity(mock_transport)
        asyncio.run(
            entity.create_agent(
                name="MY_AGENT",
                config={"model": "llama3"},
                database="DB",
                schema="SC",
                create_mode="or_replace",
            )
        )

        mock_transport.post.assert_awaited_once()
        call_args = mock_transport.post.call_args
        endpoint_used = call_args.args[0]

        assert "?" not in endpoint_used, f"async endpoint '{endpoint_used}' must not contain a query string"
        assert call_args.kwargs.get("params") == {"createMode": "or_replace"}
