"""Transport-level tests for retry and error propagation."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from cortex_agents.base import SnowflakeAPIError
from cortex_agents.core._transport import AsyncTransport, SyncTransport


def _make_transport(session: httpx.Client) -> SyncTransport:
    return SyncTransport(
        session=session,
        build_url=lambda endpoint: f"https://example.com/{endpoint}",
        log_request=lambda *args: None,
        log_response=lambda *args: None,
        logger=logging.getLogger("test.transport.sync"),
    )


def _make_async_transport(client: httpx.AsyncClient) -> AsyncTransport:
    return AsyncTransport(
        client=client,
        build_url=lambda endpoint: f"https://example.com/{endpoint}",
        log_request=lambda *args: None,
        log_response=lambda *args: None,
        logger=logging.getLogger("test.transport.async"),
    )


def _make_response(
    method: str,
    status_code: int,
    *,
    json_body: dict | None = None,
    text: str = "",
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    request = httpx.Request(method, "https://example.com/test")
    if json_body is not None:
        return httpx.Response(status_code, request=request, json=json_body, headers=headers)
    return httpx.Response(status_code, request=request, text=text, headers=headers)


class TestSyncTransportRetries:
    @pytest.mark.parametrize(
        ("method_name", "call_args", "session_method"),
        [
            ("get", ("agents", {"limit": 1}), "get"),
            ("post", ("agents", {"name": "demo"}), "post"),
            ("put", ("agents/demo", {"name": "demo"}), "put"),
            ("delete", ("agents/demo", {"ifExists": "true"}), "delete"),
        ],
    )
    def test_retryable_status_retries_and_recovers(
        self,
        monkeypatch: pytest.MonkeyPatch,
        method_name: str,
        call_args: tuple,
        session_method: str,
    ):
        monkeypatch.setattr("cortex_agents._retry.time.sleep", lambda _delay: None)

        session = Mock(spec=httpx.Client)
        getattr(session, session_method).side_effect = [
            _make_response("GET", 503, text="temporary failure"),
            _make_response("GET", 200, json_body={"status": "ok"}),
        ]
        transport = _make_transport(session)

        result = getattr(transport, method_name)(*call_args)

        assert result == {"status": "ok"}
        assert getattr(session, session_method).call_count == 2

    def test_non_retryable_error_preserves_snowflake_request_id(self) -> None:
        session = Mock(spec=httpx.Client)
        session.get.return_value = _make_response(
            "GET",
            404,
            text="not found",
            headers={"x-snowflake-request-id": "sf-404"},
        )
        transport = _make_transport(session)

        with pytest.raises(SnowflakeAPIError) as exc_info:
            transport.get("agents/demo")

        assert exc_info.value.status_code == 404
        assert exc_info.value.request_id == "sf-404"


class TestAsyncTransportRetries:
    def test_retryable_status_retries_and_recovers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def noop_sleep(_delay: float) -> None:
            return None

        monkeypatch.setattr("cortex_agents._retry.asyncio.sleep", noop_sleep)

        async def run_scenario() -> None:
            client = AsyncMock(spec=httpx.AsyncClient)
            client.get.side_effect = [
                _make_response("GET", 503, text="temporary failure"),
                _make_response("GET", 200, json_body={"status": "ok"}),
            ]
            transport = _make_async_transport(client)

            result = await transport.get("agents", {"limit": 1})

            assert result == {"status": "ok"}
            assert client.get.await_count == 2

        asyncio.run(run_scenario())

    def test_non_retryable_error_preserves_snowflake_request_id(self) -> None:
        async def run_scenario() -> None:
            client = AsyncMock(spec=httpx.AsyncClient)
            client.get.return_value = _make_response(
                "GET",
                404,
                text="not found",
                headers={"x-snowflake-request-id": "sf-async-404"},
            )
            transport = _make_async_transport(client)

            with pytest.raises(SnowflakeAPIError) as exc_info:
                await transport.get("agents/demo")

            assert exc_info.value.status_code == 404
            assert exc_info.value.request_id == "sf-async-404"

        asyncio.run(run_scenario())
