"""
Utility functions for Snowflake Cortex Agents.

This module provides shared utility functions used across the SDK.
"""

import os
from urllib.parse import urlparse

# Optional dotenv support - only load if available
try:
    from dotenv import find_dotenv, load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


def validate_account_url(url: str) -> str:
    """Validate and normalize Snowflake account URL.

    Ensures the URL has https:// scheme, ends with snowflakecomputing.com,
    and has no trailing slashes.

    Args:
        url: Account URL to validate.

    Returns:
        Normalized account URL.

    Raises:
        ValueError: If URL format is invalid.

    Examples:
        >>> validate_account_url("myaccount.snowflakecomputing.com")
        "https://myaccount.snowflakecomputing.com"

        >>> validate_account_url("https://myaccount.snowflakecomputing.com/")
        "https://myaccount.snowflakecomputing.com"

        >>> validate_account_url("https://myaccount.us-east-1.snowflakecomputing.com")
        "https://myaccount.us-east-1.snowflakecomputing.com"
    """
    if not url:
        raise ValueError("account_url cannot be empty")

    # Remove trailing slashes
    url = url.rstrip("/")

    # Add https:// if missing
    if not url.startswith("https://") and not url.startswith("http://"):
        url = f"https://{url}"

    # Validate snowflakecomputing.com domain
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname != "snowflakecomputing.com" and not hostname.endswith(".snowflakecomputing.com"):
        raise ValueError(
            f"Invalid account_url: '{url}'. Expected format: https://<account_identifier>.snowflakecomputing.com"
        )

    # Ensure https (not http)
    if url.startswith("http://"):
        raise ValueError(f"Invalid account_url: '{url}'. Must use https:// (not http://)")

    return url


def load_credentials(account_url: str | None = None, pat: str | None = None) -> tuple[str, str]:
    """Load Snowflake account URL and personal access token.

    Tries provided parameters first, then falls back to environment variables.
    Automatically validates and normalizes the account URL.

    Args:
        account_url: Snowflake account URL. Falls back to SNOWFLAKE_ACCOUNT_URL
            environment variable if not provided.
        pat: Personal access token. Falls back to SNOWFLAKE_PAT environment
            variable if not provided.

    Returns:
        Tuple of (validated_account_url, pat).

    Raises:
        ValueError: If credentials are not provided or account_url format is
            invalid.

    Examples:
        >>> # Load from environment variables
        >>> url, token = load_credentials()

        >>> # Provide explicit credentials
        >>> url, token = load_credentials(
        ...     account_url="myaccount.snowflakecomputing.com",
        ...     pat="my-token-123"
        ... )

        >>> # Mix: URL from param, PAT from env
        >>> url, token = load_credentials(
        ...     account_url="myaccount.snowflakecomputing.com"
        ... )

    Note:
        If python-dotenv is installed, .env files will be automatically loaded.
        Otherwise, only system environment variables will be used.
    """
    # Load environment variables from .env file if dotenv is available
    # Use override=False to respect already-set environment variables (e.g., in tests)
    if HAS_DOTENV:
        load_dotenv(find_dotenv(), override=False)

    # Get credentials from params or environment
    final_account_url: str | None = account_url or os.getenv("SNOWFLAKE_ACCOUNT_URL")
    final_pat: str | None = pat or os.getenv("SNOWFLAKE_PAT")

    # Validate both are provided
    if not final_account_url or not final_pat:
        raise ValueError(
            "Missing required credentials. Provide account_url and pat as parameters "
            "or set SNOWFLAKE_ACCOUNT_URL and SNOWFLAKE_PAT environment variables."
        )

    # Validate and normalize account URL
    final_account_url = validate_account_url(final_account_url)

    return final_account_url, final_pat
