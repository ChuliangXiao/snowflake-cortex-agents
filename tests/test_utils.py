"""Tests for utils module."""

import pytest

from cortex_agents.utils import load_credentials, validate_account_url


class TestValidateAccountUrl:
    """Tests for validate_account_url function."""

    def test_adds_https_prefix(self):
        """Should add https:// if missing."""
        result = validate_account_url("myaccount.snowflakecomputing.com")
        assert result == "https://myaccount.snowflakecomputing.com"

    def test_removes_trailing_slashes(self):
        """Should remove trailing slashes."""
        result = validate_account_url("https://myaccount.snowflakecomputing.com/")
        assert result == "https://myaccount.snowflakecomputing.com"

    def test_accepts_regional_accounts(self):
        """Should accept regional account identifiers."""
        result = validate_account_url("https://myaccount.us-east-1.snowflakecomputing.com")
        assert result == "https://myaccount.us-east-1.snowflakecomputing.com"

    def test_rejects_http(self):
        """Should reject http:// URLs."""
        with pytest.raises(ValueError, match="Must use https://"):
            validate_account_url("http://myaccount.snowflakecomputing.com")

    def test_rejects_invalid_domain(self):
        """Should reject non-Snowflake domains."""
        with pytest.raises(ValueError, match="Expected format"):
            validate_account_url("https://myaccount.example.com")

    def test_rejects_empty_string(self):
        """Should reject empty strings."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_account_url("")


class TestLoadCredentials:
    """Tests for load_credentials function."""

    def test_loads_from_parameters(self):
        """Should use provided parameters."""
        url, pat = load_credentials(account_url="myaccount.snowflakecomputing.com", pat="test-token")
        assert url == "https://myaccount.snowflakecomputing.com"
        assert pat == "test-token"

    def test_loads_from_environment(self, monkeypatch):
        """Should fall back to environment variables."""
        monkeypatch.setenv("SNOWFLAKE_ACCOUNT_URL", "envaccount.snowflakecomputing.com")
        monkeypatch.setenv("SNOWFLAKE_PAT", "env-token")

        url, pat = load_credentials()
        assert url == "https://envaccount.snowflakecomputing.com"
        assert pat == "env-token"

    def test_parameters_override_environment(self, monkeypatch):
        """Parameters should take precedence over env vars."""
        monkeypatch.setenv("SNOWFLAKE_ACCOUNT_URL", "envaccount.snowflakecomputing.com")
        monkeypatch.setenv("SNOWFLAKE_PAT", "env-token")

        url, pat = load_credentials(account_url="paramaccount.snowflakecomputing.com", pat="param-token")
        assert url == "https://paramaccount.snowflakecomputing.com"
        assert pat == "param-token"

    def test_raises_on_missing_credentials(self, clean_environment):
        """Should raise ValueError if credentials not found."""
        with pytest.raises(ValueError, match="Missing required credentials"):
            load_credentials()

    def test_validates_account_url(self):
        """Should validate account URL format."""
        with pytest.raises(ValueError, match="Expected format"):
            load_credentials(account_url="invalid.example.com", pat="test-token")
