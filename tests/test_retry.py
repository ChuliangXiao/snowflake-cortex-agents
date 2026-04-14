"""Tests for _retry module."""

import asyncio
from unittest.mock import Mock

import httpx
import pytest

from cortex_agents._retry import (
    _handle_retry_attempt,
    _should_retry_exception,
    _should_retry_status,
    retry_with_backoff,
)
from cortex_agents.base import SnowflakeAPIError


class TestShouldRetryStatus:
    """Tests for _should_retry_status function."""

    def test_retry_429(self):
        """Should retry on 429 (rate limit)."""
        assert _should_retry_status(429) is True

    def test_retry_500(self):
        """Should retry on 500 (internal server error)."""
        assert _should_retry_status(500) is True

    def test_retry_503(self):
        """Should retry on 503 (service unavailable)."""
        assert _should_retry_status(503) is True

    def test_no_retry_400(self):
        """Should not retry on 400 (bad request)."""
        assert _should_retry_status(400) is False

    def test_no_retry_404(self):
        """Should not retry on 404 (not found)."""
        assert _should_retry_status(404) is False

    def test_no_retry_none(self):
        """Should not retry on None status."""
        assert _should_retry_status(None) is False


class TestShouldRetryException:
    """Tests for _should_retry_exception function."""

    def test_retry_timeout_exception(self):
        """Should retry on timeout."""
        exc = httpx.TimeoutException("Timeout")
        should_retry, status = _should_retry_exception(exc)
        assert should_retry is True
        assert status is None

    def test_retry_connect_error(self):
        """Should retry on connection error."""
        exc = httpx.ConnectError("Connection failed")
        should_retry, status = _should_retry_exception(exc)
        assert should_retry is True
        assert status is None

    def test_retry_http_status_error_500(self):
        """Should retry on 500 HTTP status error."""
        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(500, request=request)
        exc = httpx.HTTPStatusError("Server error", request=request, response=response)
        should_retry, status = _should_retry_exception(exc)
        assert should_retry is True
        assert status == 500

    def test_retry_snowflake_api_error_503(self):
        """Should retry on SnowflakeAPIError when it wraps a retryable status."""
        exc = SnowflakeAPIError("Service unavailable", status_code=503)
        should_retry, status = _should_retry_exception(exc)
        assert should_retry is True
        assert status == 503

    def test_no_retry_http_status_error_404(self):
        """Should not retry on 404 HTTP status error."""
        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(404, request=request)
        exc = httpx.HTTPStatusError("Not found", request=request, response=response)
        should_retry, status = _should_retry_exception(exc)
        assert should_retry is False
        assert status == 404

    def test_no_retry_value_error(self):
        """Should not retry on non-HTTP errors."""
        exc = ValueError("Invalid value")
        should_retry, status = _should_retry_exception(exc)
        assert should_retry is False
        assert status is None


class TestHandleRetryAttempt:
    """Tests for _handle_retry_attempt function."""

    def test_reraises_non_retryable_exception(self):
        """Should re-raise non-retryable exceptions."""
        exc = ValueError("Not retryable")
        with pytest.raises(ValueError, match="Not retryable"):
            try:
                raise exc
            except Exception as e:
                _handle_retry_attempt(e, 1, 3, "test_func")

    def test_reraises_on_max_attempts(self):
        """Should re-raise when max attempts reached."""
        exc = httpx.TimeoutException("Timeout")
        with pytest.raises(httpx.TimeoutException):
            try:
                raise exc
            except Exception as e:
                _handle_retry_attempt(e, 3, 3, "test_func")

    def test_returns_true_for_retryable_exception(self):
        """Should return True for retryable exceptions below max attempts."""
        exc = httpx.TimeoutException("Timeout")
        should_continue, status = _handle_retry_attempt(exc, 1, 3, "test_func")
        assert should_continue is True
        assert status is None

    def test_returns_status_for_http_error(self):
        """Should return status code for HTTP errors."""
        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("Service unavailable", request=request, response=response)
        should_continue, status = _handle_retry_attempt(exc, 1, 3, "test_func")
        assert should_continue is True
        assert status == 503


class TestRetryWithBackoff:
    """Tests for retry_with_backoff decorator."""

    def test_sync_function_succeeds_first_try(self):
        """Should return result on first successful attempt."""
        mock_func = Mock(return_value="success")

        @retry_with_backoff(max_attempts=3)
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 1

    def test_sync_function_retries_on_timeout(self):
        """Should retry on timeout exception."""
        mock_func = Mock(side_effect=[httpx.TimeoutException("Timeout"), "success"])

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_sync_function_retries_on_500(self):
        """Should retry on 500 HTTP error."""
        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(500, request=request)
        exc = httpx.HTTPStatusError("Server error", request=request, response=response)
        mock_func = Mock(side_effect=[exc, "success"])

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_sync_function_no_retry_on_404(self):
        """Should not retry on 404 HTTP error."""
        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(404, request=request)
        exc = httpx.HTTPStatusError("Not found", request=request, response=response)
        mock_func = Mock(side_effect=exc)

        @retry_with_backoff(max_attempts=3)
        def test_func():
            return mock_func()

        with pytest.raises(httpx.HTTPStatusError):
            test_func()
        assert mock_func.call_count == 1

    def test_sync_function_exhausts_retries(self):
        """Should raise exception after max attempts."""
        mock_func = Mock(side_effect=httpx.TimeoutException("Timeout"))

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def test_func():
            return mock_func()

        with pytest.raises(httpx.TimeoutException):
            test_func()
        assert mock_func.call_count == 3

    def test_async_function_succeeds_first_try(self):
        """Should return result on first successful attempt (async)."""
        mock_func = Mock(return_value="success")

        @retry_with_backoff(max_attempts=3)
        async def test_func():
            return mock_func()

        result = asyncio.run(test_func())
        assert result == "success"
        assert mock_func.call_count == 1

    def test_async_function_retries_on_timeout(self):
        """Should retry on timeout exception (async)."""
        mock_func = Mock(side_effect=[httpx.TimeoutException("Timeout"), "success"])

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        async def test_func():
            return mock_func()

        result = asyncio.run(test_func())
        assert result == "success"
        assert mock_func.call_count == 2

    def test_async_function_exhausts_retries(self):
        """Should raise exception after max attempts (async)."""
        mock_func = Mock(side_effect=httpx.TimeoutException("Timeout"))

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        async def test_func():
            return mock_func()

        with pytest.raises(httpx.TimeoutException):
            asyncio.run(test_func())
        assert mock_func.call_count == 3

    def test_exponential_backoff_delay(self):
        """Should increase delay exponentially."""
        attempts = []

        @retry_with_backoff(max_attempts=3, base_delay=0.01, exponential_base=2.0)
        def test_func():
            attempts.append(1)
            if len(attempts) < 3:
                raise httpx.TimeoutException("Timeout")
            return "success"

        result = test_func()
        assert result == "success"
        assert len(attempts) == 3

    def test_max_delay_cap(self):
        """Should cap delay at max_delay."""

        @retry_with_backoff(max_attempts=5, base_delay=1.0, max_delay=2.0, exponential_base=3.0)
        def test_func():
            raise httpx.TimeoutException("Timeout")

        with pytest.raises(httpx.TimeoutException):
            test_func()
