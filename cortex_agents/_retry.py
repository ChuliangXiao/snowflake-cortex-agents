"""Retry decorators with exponential backoff for HTTP requests.

Provides decorators for both sync and async functions to handle transient
errors with automatic retries and exponential backoff.
"""

import asyncio
import inspect
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

import httpx

from .base import SnowflakeAPIError

logger: logging.Logger = logging.getLogger(__name__)


def _callable_name(func: Callable[..., Any]) -> str:
    """Return a stable display name for a callable."""
    name = getattr(func, "__name__", None)
    if isinstance(name, str):
        return name
    return func.__class__.__name__


def _should_retry_status(status_code: int | None) -> bool:
    """Check if an HTTP status code should trigger a retry.

    Args:
        status_code: HTTP status code to check.

    Returns:
        True if the status code indicates a retryable error (429 or 5xx).
    """
    return status_code == 429 or (status_code is not None and status_code >= 500)


def _should_retry_exception(exc: Exception) -> tuple[bool, int | None]:
    """Determine if an exception should trigger a retry.

    Args:
        exc: Exception to evaluate.

    Returns:
        Tuple of (should_retry, status_code). status_code is None for non-HTTP errors.
    """
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return (True, None)
    elif isinstance(exc, SnowflakeAPIError):
        return (_should_retry_status(exc.status_code), exc.status_code)
    elif isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code if exc.response else None
        return (_should_retry_status(status_code), status_code)
    return (False, None)


def _handle_retry_attempt(
    exc: Exception,
    attempt: int,
    max_attempts: int,
    func_name: str,
    delay: float = 0.0,
) -> tuple[bool, int | None]:
    """Process a retry attempt and determine if retry should continue.

    Args:
        exc: Exception that was raised.
        attempt: Current attempt number.
        max_attempts: Maximum number of attempts allowed.
        func_name: Name of the function being retried.
        delay: Current backoff delay in seconds (for log messages).

    Returns:
        Tuple of (should_continue, status_code). should_continue is False if max attempts reached.

    Raises:
        Exception: Re-raises the exception if it shouldn't be retried or max attempts exceeded.
    """
    should_retry, status_code = _should_retry_exception(exc)

    if not should_retry:
        raise

    if attempt >= max_attempts:
        logger.error(f"Max retries exceeded for {func_name}", exc_info=True)
        raise

    if status_code is not None:
        logger.warning(f"HTTP {status_code} for {func_name}, retrying in {delay}s")
    else:
        logger.warning(f"Attempt {attempt} failed for {func_name}, retrying in {delay}s: {exc}")

    return (True, status_code)


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 32.0,
    exponential_base: float = 2.0,
) -> Callable:
    """Decorator for retrying functions with exponential backoff.

    Automatically detects sync/async functions and retries those that raise
    httpx.TimeoutException, httpx.ConnectError, or httpx.HTTPStatusError
    (for retryable status codes).

    Args:
        max_attempts: Maximum number of retry attempts. Defaults to 3.
        base_delay: Initial delay in seconds before first retry. Defaults to 1.0.
        max_delay: Maximum delay between retries. Defaults to 32.0.
        exponential_base: Base for exponential backoff calculation. Defaults to 2.0.

    Returns:
        Decorated function with retry logic.
    """

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                attempt = 0
                delay = base_delay

                while attempt < max_attempts:
                    try:
                        return await func(*args, **kwargs)
                    except Exception as exc:
                        attempt += 1
                        _handle_retry_attempt(exc, attempt, max_attempts, _callable_name(func), delay)
                        await asyncio.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                attempt = 0
                delay = base_delay

                while attempt < max_attempts:
                    try:
                        return func(*args, **kwargs)
                    except Exception as exc:
                        attempt += 1
                        _handle_retry_attempt(exc, attempt, max_attempts, _callable_name(func), delay)
                        time.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)

            return sync_wrapper

    return decorator
