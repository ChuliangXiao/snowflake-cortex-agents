"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def mock_snowflake_credentials(monkeypatch):
    """Provide mock Snowflake credentials for testing."""
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT_URL", "testaccount.snowflakecomputing.com")
    monkeypatch.setenv("SNOWFLAKE_PAT", "test-token-123")
    return {"account_url": "https://testaccount.snowflakecomputing.com", "pat": "test-token-123"}


@pytest.fixture
def clean_environment(monkeypatch):
    """Clean environment variables for testing."""
    monkeypatch.delenv("SNOWFLAKE_ACCOUNT_URL", raising=False)
    monkeypatch.delenv("SNOWFLAKE_PAT", raising=False)
    # Mock find_dotenv to return empty string so .env file is not loaded
    monkeypatch.setattr("cortex_agents.utils.find_dotenv", lambda: "")
