"""Shared HTTP transport helpers for Cortex clients."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass
from typing import Any, Literal, overload

import httpx

from .._retry import retry_with_backoff
from .._streaming import create_async_stream_with_retry, create_stream_with_retry
from ..base import SnowflakeAPIError, request_id_ctx

JsonDict = dict[str, Any]


def _get_response_request_id(response: httpx.Response, fallback_request_id: str) -> str:
    """Return Snowflake's request ID when present, otherwise the local fallback."""
    snowflake_request_id = response.headers.get("x-snowflake-request-id")
    if snowflake_request_id:
        request_id_ctx.set(snowflake_request_id)
        return snowflake_request_id
    return fallback_request_id


def _log_snowflake_request_id(
    logger_instance: logging.Logger,
    method: str,
    endpoint: str,
    response: httpx.Response,
) -> None:
    """Emit the Snowflake request ID for easier server-side trace correlation."""
    snowflake_request_id = response.headers.get("x-snowflake-request-id")
    if snowflake_request_id:
        logger_instance.debug(f"{method} {endpoint} - Snowflake request_id: {snowflake_request_id}")


def _raise_api_error(
    method: str,
    endpoint: str,
    response: httpx.Response,
    fallback_request_id: str,
    exc: httpx.HTTPStatusError,
) -> None:
    """Raise the SDK error type with HTTP context preserved."""
    raise SnowflakeAPIError(
        f"{method} {endpoint} failed",
        status_code=response.status_code,
        request_id=_get_response_request_id(response, fallback_request_id),
        response_body=response.text,
    ) from exc


def _parse_json_response(response: httpx.Response) -> JsonDict:
    """Parse JSON response, handling empty bodies gracefully.

    Some Snowflake API endpoints return empty bodies on success,
    even with Content-Type: application/json header.

    Args:
        response: The httpx response object

    Returns:
        Parsed JSON dict or ``{"status": "success"}`` for empty responses.

    Raises:
        SnowflakeAPIError: If the response contains a non-empty body that
            cannot be parsed as JSON.
    """
    if not response.text or response.text.strip() == "":
        return {"status": "success"}

    try:
        return response.json()
    except ValueError as exc:
        raise SnowflakeAPIError(
            f"Response returned invalid JSON (HTTP {response.status_code})",
            status_code=response.status_code,
            response_body=response.text,
        ) from exc


@dataclass
class SyncTransport:
    """Thin wrapper around an httpx.Client with retry, logging, and streaming support."""

    session: httpx.Client
    build_url: Callable[[str], str]
    log_request: Callable[[str, str, str], None]
    log_response: Callable[[str, str, int, str], None]
    logger: logging.Logger

    @retry_with_backoff(max_attempts=3)
    def get(self, endpoint: str, params: JsonDict | None = None) -> JsonDict:
        req_id = str(uuid.uuid4())
        request_id_ctx.set(req_id)

        url = self.build_url(endpoint)
        self.log_request("GET", endpoint, req_id)

        response = self.session.get(url, params=params)
        self.log_response("GET", endpoint, response.status_code, req_id)
        _log_snowflake_request_id(self.logger, "GET", endpoint, response)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _raise_api_error("GET", endpoint, response, req_id, exc)

        return _parse_json_response(response)

    @retry_with_backoff(max_attempts=3)
    def _post_json(self, endpoint: str, url: str, json_data: JsonDict, params: JsonDict | None = None) -> JsonDict:
        """Non-streaming POST with retry via decorator."""
        req_id = str(uuid.uuid4())
        request_id_ctx.set(req_id)

        self.log_request("POST", endpoint, req_id)
        response = self.session.post(url, json=json_data, params=params)
        self.log_response("POST", endpoint, response.status_code, req_id)
        _log_snowflake_request_id(self.logger, "POST", endpoint, response)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _raise_api_error("POST", endpoint, response, req_id, exc)

        return _parse_json_response(response)

    @overload
    def post(
        self, endpoint: str, json_data: JsonDict, *, params: JsonDict | None = None, stream: Literal[False] = False
    ) -> JsonDict: ...

    @overload
    def post(
        self, endpoint: str, json_data: JsonDict, *, params: JsonDict | None = None, stream: Literal[True]
    ) -> Callable[[], AbstractContextManager[httpx.Response]]: ...

    def post(
        self,
        endpoint: str,
        json_data: JsonDict,
        *,
        params: JsonDict | None = None,
        stream: bool = False,
    ) -> Callable[[], AbstractContextManager[httpx.Response]] | JsonDict:
        """POST a JSON payload; return a stream factory or parsed JSON.

        Streaming requests are handled by ``create_stream_with_retry`` which
        carries its own retry loop.  Non-streaming requests are delegated to
        ``_post_json`` which is decorated with ``@retry_with_backoff``.
        """
        url = self.build_url(endpoint)

        if stream:
            return create_stream_with_retry(
                self.session,
                endpoint,
                url,
                json_data,
                params=params,
                log_request=self.log_request,
                log_response=self.log_response,
                logger_instance=self.logger,
            )

        return self._post_json(endpoint, url, json_data, params=params)

    @retry_with_backoff(max_attempts=3)
    def put(self, endpoint: str, json_data: JsonDict) -> JsonDict:
        req_id = str(uuid.uuid4())
        request_id_ctx.set(req_id)

        url = self.build_url(endpoint)
        self.log_request("PUT", endpoint, req_id)

        response = self.session.put(url, json=json_data)
        self.log_response("PUT", endpoint, response.status_code, req_id)
        _log_snowflake_request_id(self.logger, "PUT", endpoint, response)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _raise_api_error("PUT", endpoint, response, req_id, exc)

        return _parse_json_response(response)

    @retry_with_backoff(max_attempts=3)
    def delete(self, endpoint: str, params: JsonDict | None = None) -> JsonDict:
        req_id = str(uuid.uuid4())
        request_id_ctx.set(req_id)

        url = self.build_url(endpoint)
        self.log_request("DELETE", endpoint, req_id)

        response = self.session.delete(url, params=params)
        self.log_response("DELETE", endpoint, response.status_code, req_id)
        _log_snowflake_request_id(self.logger, "DELETE", endpoint, response)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _raise_api_error("DELETE", endpoint, response, req_id, exc)

        return _parse_json_response(response)


@dataclass
class AsyncTransport:
    """Async counterpart to ``SyncTransport`` built on httpx.AsyncClient."""

    client: httpx.AsyncClient
    build_url: Callable[[str], str]
    log_request: Callable[[str, str, str], None]
    log_response: Callable[[str, str, int, str], None]
    logger: logging.Logger

    @retry_with_backoff(max_attempts=3)
    async def get(self, endpoint: str, params: JsonDict | None = None) -> JsonDict:
        if self.client is None:
            raise SnowflakeAPIError("Client not initialized. Use async with context manager.")

        req_id = str(uuid.uuid4())
        request_id_ctx.set(req_id)

        url = self.build_url(endpoint)
        self.log_request("GET", endpoint, req_id)

        response = await self.client.get(url, params=params)
        self.log_response("GET", endpoint, response.status_code, req_id)
        _log_snowflake_request_id(self.logger, "GET", endpoint, response)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _raise_api_error("GET", endpoint, response, req_id, exc)

        return _parse_json_response(response)

    @retry_with_backoff(max_attempts=3)
    async def _post_json(
        self, endpoint: str, url: str, json_data: JsonDict, params: JsonDict | None = None
    ) -> JsonDict:
        """Non-streaming async POST with retry via decorator."""
        if self.client is None:
            raise SnowflakeAPIError("Client not initialized. Use async with context manager.")

        req_id = str(uuid.uuid4())
        request_id_ctx.set(req_id)

        self.log_request("POST", endpoint, req_id)
        response = await self.client.post(url, json=json_data, params=params)
        self.log_response("POST", endpoint, response.status_code, req_id)
        _log_snowflake_request_id(self.logger, "POST", endpoint, response)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _raise_api_error("POST", endpoint, response, req_id, exc)

        return _parse_json_response(response)

    @overload
    async def post(
        self, endpoint: str, json_data: JsonDict, *, params: JsonDict | None = None, stream: Literal[False] = False
    ) -> JsonDict: ...

    @overload
    async def post(
        self, endpoint: str, json_data: JsonDict, *, params: JsonDict | None = None, stream: Literal[True]
    ) -> Callable[[], AbstractAsyncContextManager[httpx.Response]]: ...

    async def post(
        self,
        endpoint: str,
        json_data: JsonDict,
        *,
        params: JsonDict | None = None,
        stream: bool = False,
    ) -> Callable[[], AbstractAsyncContextManager[httpx.Response]] | JsonDict:
        """POST a JSON payload; return a stream factory or parsed JSON.

        Streaming requests are handled by ``create_async_stream_with_retry``
        which carries its own retry loop.  Non-streaming requests are
        delegated to ``_post_json`` which is decorated with
        ``@retry_with_backoff``.
        """
        if self.client is None:
            raise SnowflakeAPIError("Client not initialized. Use async with context manager.")

        url = self.build_url(endpoint)

        if stream:
            return create_async_stream_with_retry(
                self.client,
                endpoint,
                url,
                json_data,
                params=params,
                log_request=self.log_request,
                log_response=self.log_response,
                logger_instance=self.logger,
            )

        return await self._post_json(endpoint, url, json_data, params=params)

    @retry_with_backoff(max_attempts=3)
    async def put(self, endpoint: str, json_data: JsonDict) -> JsonDict:
        if self.client is None:
            raise SnowflakeAPIError("Client not initialized. Use async with context manager.")

        req_id = str(uuid.uuid4())
        request_id_ctx.set(req_id)

        url = self.build_url(endpoint)
        self.log_request("PUT", endpoint, req_id)

        response = await self.client.put(url, json=json_data)
        self.log_response("PUT", endpoint, response.status_code, req_id)
        _log_snowflake_request_id(self.logger, "PUT", endpoint, response)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _raise_api_error("PUT", endpoint, response, req_id, exc)

        return _parse_json_response(response)

    @retry_with_backoff(max_attempts=3)
    async def delete(self, endpoint: str, params: JsonDict | None = None) -> JsonDict:
        if self.client is None:
            raise SnowflakeAPIError("Client not initialized. Use async with context manager.")

        req_id = str(uuid.uuid4())
        request_id_ctx.set(req_id)

        url = self.build_url(endpoint)
        self.log_request("DELETE", endpoint, req_id)

        response = await self.client.delete(url, params=params)
        self.log_response("DELETE", endpoint, response.status_code, req_id)
        _log_snowflake_request_id(self.logger, "DELETE", endpoint, response)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _raise_api_error("DELETE", endpoint, response, req_id, exc)

        return _parse_json_response(response)
