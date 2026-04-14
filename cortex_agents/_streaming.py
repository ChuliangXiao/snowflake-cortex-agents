"""Streaming helpers with retry logic for HTTP SSE responses.

Provides context managers for handling streaming Server-Sent Events (SSE)
responses with automatic retry, error handling, and request_id capture.
"""

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import AbstractAsyncContextManager, AbstractContextManager, asynccontextmanager, contextmanager
from typing import Any

import httpx

from ._retry import _should_retry_status

# Import request_id_ctx from base module
from .base import SnowflakeAPIError, request_id_ctx

logger: logging.Logger = logging.getLogger(__name__)


def _get_response_body_safe(response: httpx.Response | None) -> str | None:
    """Safely read response body for error reporting.

    Args:
        response: HTTP response object.

    Returns:
        Response body as string if readable, None otherwise.
    """
    if not response:
        return None
    try:
        return response.read().decode()
    except Exception:
        return None


def _handle_max_retries_error(
    endpoint: str,
    max_attempts: int,
    req_id: str,
    exc: Exception,
    logger_instance: logging.Logger,
    status_code: int | None = None,
    response_body: str | None = None,
) -> SnowflakeAPIError:
    """Create error for max retries exceeded.

    Args:
        endpoint: API endpoint that failed.
        max_attempts: Number of attempts made.
        req_id: Request ID for tracking.
        exc: Original exception.
        logger_instance: Logger for error messages.
        status_code: HTTP status code if available.
        response_body: Response body if available.

    Returns:
        SnowflakeAPIError with appropriate context.
    """
    logger_instance.error(f"Max retries exceeded for POST {endpoint}", exc_info=True)
    return SnowflakeAPIError(
        f"POST {endpoint} failed after {max_attempts} attempts",
        status_code=status_code,
        request_id=req_id,
        response_body=response_body,
    )


def create_stream_with_retry(
    session: httpx.Client,
    endpoint: str,
    url: str,
    payload: dict[str, Any],
    *,
    params: dict[str, Any] | None = None,
    log_request: Callable[[str, str, str], None],
    log_response: Callable[[str, str, int, str], None],
    logger_instance: logging.Logger,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 32.0,
    exponential_base: float = 2.0,
) -> Callable[[], AbstractContextManager[httpx.Response]]:
    """Create a retry-aware streaming context manager for sync clients.

    Returns a callable that produces a context manager for streaming HTTP
    responses. Includes automatic retry with exponential backoff for
    transient errors, and captures the Snowflake request_id from response
    headers.

    Args:
        session: httpx.Client instance for making requests.
        endpoint: API endpoint path for logging.
        url: Full URL to make the streaming request to.
        payload: JSON payload for the POST request.
        log_request: Callback for logging request details.
        log_response: Callback for logging response details.
        logger_instance: Logger instance for this streaming operation.
        max_attempts: Maximum number of retry attempts. Defaults to 3.
        base_delay: Initial delay in seconds before first retry. Defaults to 1.0.
        max_delay: Maximum delay between retries. Defaults to 32.0.
        exponential_base: Base for exponential backoff calculation. Defaults to 2.0.

    Returns:
        Callable that returns an Iterator context manager yielding httpx.Response.

    The response object will have a request_id attribute set from the
    x-snowflake-request-id header if present.
    """

    @contextmanager
    def streamer() -> Iterator[httpx.Response]:
        attempt = 0
        delay = base_delay

        while True:
            req_id = str(uuid.uuid4())
            request_id_ctx.set(req_id)
            log_request("POST", endpoint, req_id)

            try:
                with session.stream(
                    "POST",
                    url,
                    json=payload,
                    params=params,
                    headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"},
                ) as response:
                    log_response("POST", endpoint, response.status_code, req_id)
                    response.raise_for_status()

                    yield response
                    return

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                attempt += 1
                if attempt >= max_attempts:
                    raise _handle_max_retries_error(endpoint, max_attempts, req_id, exc, logger_instance) from exc

                logger_instance.warning(f"Attempt {attempt} failed for POST {endpoint}, retrying in {delay}s: {exc}")
                time.sleep(delay)
                delay = min(delay * exponential_base, max_delay)

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response else None
                response_body = _get_response_body_safe(exc.response)

                if _should_retry_status(status_code):
                    attempt += 1
                    if attempt >= max_attempts:
                        raise _handle_max_retries_error(
                            endpoint, max_attempts, req_id, exc, logger_instance, status_code, response_body
                        ) from exc

                    logger_instance.warning(f"HTTP {status_code} for POST {endpoint}, retrying in {delay}s")
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
                else:
                    raise SnowflakeAPIError(
                        f"POST {endpoint} failed",
                        status_code=status_code,
                        request_id=req_id,
                        response_body=response_body,
                    ) from exc

    return streamer


def create_async_stream_with_retry(
    client: httpx.AsyncClient,
    endpoint: str,
    url: str,
    payload: dict[str, Any],
    *,
    params: dict[str, Any] | None = None,
    log_request: Callable[[str, str, str], None],
    log_response: Callable[[str, str, int, str], None],
    logger_instance: logging.Logger,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 32.0,
    exponential_base: float = 2.0,
) -> Callable[[], AbstractAsyncContextManager[httpx.Response]]:
    """Create a retry-aware streaming context manager for async clients.

    Returns a callable that produces an async context manager for streaming
    HTTP responses. Includes automatic retry with exponential backoff for
    transient errors, and captures the Snowflake request_id from response
    headers.

    Args:
        client: httpx.AsyncClient instance for making requests.
        endpoint: API endpoint path for logging.
        url: Full URL to make the streaming request to.
        payload: JSON payload for the POST request.
        log_request: Callback for logging request details.
        log_response: Callback for logging response details.
        logger_instance: Logger instance for this streaming operation.
        max_attempts: Maximum number of retry attempts. Defaults to 3.
        base_delay: Initial delay in seconds before first retry. Defaults to 1.0.
        max_delay: Maximum delay between retries. Defaults to 32.0.
        exponential_base: Base for exponential backoff calculation. Defaults to 2.0.

    Returns:
        Callable that returns an AsyncIterator context manager yielding httpx.Response.

    The response object will have a request_id attribute set from the
    x-snowflake-request-id header if present.
    """

    if client is None:
        raise SnowflakeAPIError("Client not initialized. Use async with context manager.")

    @asynccontextmanager
    async def streamer() -> AsyncIterator[httpx.Response]:
        attempt = 0
        delay = base_delay

        while True:
            req_id = str(uuid.uuid4())
            request_id_ctx.set(req_id)
            log_request("POST", endpoint, req_id)

            try:
                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    params=params,
                    headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"},
                ) as response:
                    log_response("POST", endpoint, response.status_code, req_id)
                    response.raise_for_status()

                    yield response
                    return

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                attempt += 1
                if attempt >= max_attempts:
                    raise _handle_max_retries_error(endpoint, max_attempts, req_id, exc, logger_instance) from exc

                logger_instance.warning(f"Attempt {attempt} failed for POST {endpoint}, retrying in {delay}s: {exc}")
                await asyncio.sleep(delay)
                delay = min(delay * exponential_base, max_delay)

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response else None
                response_body = _get_response_body_safe(exc.response)

                if _should_retry_status(status_code):
                    attempt += 1
                    if attempt >= max_attempts:
                        raise _handle_max_retries_error(
                            endpoint, max_attempts, req_id, exc, logger_instance, status_code, response_body
                        ) from exc

                    logger_instance.warning(f"HTTP {status_code} for POST {endpoint}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
                else:
                    raise SnowflakeAPIError(
                        f"POST {endpoint} failed",
                        status_code=status_code,
                        request_id=req_id,
                        response_body=response_body,
                    ) from exc

    return streamer
