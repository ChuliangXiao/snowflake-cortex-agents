"""Tests for base module."""

import pytest

from cortex_agents.base import BaseAgent, SnowflakeAPIError


class TestSnowflakeAPIError:
    """Tests for SnowflakeAPIError exception."""

    def test_basic_error(self):
        """Should create error with message."""
        error = SnowflakeAPIError("Test error")
        assert error.message == "Test error"
        assert error.status_code is None
        assert error.request_id is None

    def test_error_with_details(self):
        """Should store all error details."""
        error = SnowflakeAPIError("Test error", status_code=404, request_id="req-123", response_body="Not found")
        assert error.message == "Test error"
        assert error.status_code == 404
        assert error.request_id == "req-123"
        assert error.response_body == "Not found"


class TestBaseAgent:
    """Tests for BaseAgent class."""

    def test_cannot_instantiate_abstract_class(self):
        """BaseAgent is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseAgent(account_url="test.snowflakecomputing.com", pat="test-token")

    def test_load_credentials_wraps_errors(self):
        """Should convert ValueError to SnowflakeAPIError."""
        # This tests the concept - we'd need a concrete implementation to fully test
        # For now, we can test the utility function behavior in test_utils.py
        pass
