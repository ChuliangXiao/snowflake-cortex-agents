"""Base classes and interfaces for Cortex SDK.

Defines common patterns and abstractions used across Agent and Analyst clients.
"""

import logging
from abc import ABC, abstractmethod
from contextvars import ContextVar
from urllib.parse import quote

from .utils import load_credentials

logger: logging.Logger = logging.getLogger(__name__)
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class SnowflakeAPIError(Exception):
    """Custom exception for Snowflake API errors.

    Attributes:
        message: Error message
        status_code: HTTP status code (if applicable)
        request_id: Snowflake request ID (if applicable)
        response_body: Raw response body (if applicable)
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        request_id: str | None = None,
        response_body: str | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.response_body = response_body
        super().__init__(self.message)


class BaseAgent(ABC):
    """Base class for Cortex Agent and Analyst clients.

    Provides shared functionality for credential management and validation, URL
    construction, and request/response logging.

    Attributes:
        account_url (str): Snowflake account URL.
        pat (str): Personal access token.
    """

    def __init__(
        self,
        account_url: str | None = None,
        pat: str | None = None,
        enable_logging: bool = True,
        token_type: str | None = None,
    ) -> None:
        """Initialize base agent.

        Args:
            account_url: Snowflake account URL. Defaults to SNOWFLAKE_ACCOUNT_URL
                environment variable.
            pat: Personal access token. Defaults to SNOWFLAKE_PAT environment
                variable.
            enable_logging: Enable request/response logging. Defaults to True.
            token_type: Authorization token type. Set to ``"KEYPAIR_JWT"`` when
                authenticating with a key-pair JWT instead of a PAT. When
                provided, the ``X-Snowflake-Authorization-Token-Type`` header
                is included in all requests.
        """
        self._enable_logging = enable_logging
        self._token_type = token_type
        self.account_url: str
        self.pat: str
        self.account_url, self.pat = self._load_credentials(account_url, pat)

    def _load_credentials(self, account_url: str | None = None, pat: str | None = None) -> tuple[str, str]:
        """Load Snowflake account URL and personal access token.

        Wraps utils.load_credentials and converts ValueError to SnowflakeAPIError
        for consistency.

        Args:
            account_url: Snowflake account URL (optional).
            pat: Personal access token (optional).

        Returns:
            Tuple of (account_url, pat).

        Raises:
            SnowflakeAPIError: If credentials are not provided or invalid.
        """
        try:
            return load_credentials(account_url, pat)
        except ValueError as e:
            raise SnowflakeAPIError(str(e)) from e

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers for the client, including auth and optional token type.

        Returns:
            Dict of header name to header value.
        """
        headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json",
        }
        if self._token_type:
            headers["X-Snowflake-Authorization-Token-Type"] = self._token_type
        return headers

    def _get_url(self, endpoint: str) -> str:
        """Build full API URL from endpoint.

        Each path segment is percent-encoded to prevent path-traversal or
        injection via user-supplied database/schema/agent names.

        Args:
            endpoint: API endpoint path (e.g. ``databases/MY_DB/schemas/S/agents/A:run``).

        Returns:
            Full API URL with encoded path segments.
        """
        stripped = endpoint.lstrip("/")
        # Encode each segment individually, preserving '/' separators
        # and ':action' suffixes (e.g. ':run', ':feedback')
        encoded_segments = []
        for segment in stripped.split("/"):
            if ":" in segment:
                name, action = segment.rsplit(":", 1)
                encoded_segments.append(f"{quote(name, safe='')}:{quote(action, safe='')}")
            else:
                encoded_segments.append(quote(segment, safe=""))
        return f"{self.account_url}/api/v2/{'/'.join(encoded_segments)}"

    def _log_request(self, method: str, endpoint: str, request_id: str) -> None:
        """Log HTTP request details.

        Args:
            method: HTTP method (GET, POST, PUT, etc.).
            endpoint: API endpoint path.
            request_id: Unique request identifier.
        """
        if self._enable_logging:
            logger.debug(
                f"{method} {endpoint}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "endpoint": endpoint,
                },
            )

    def _log_response(self, method: str, endpoint: str, status_code: int, request_id: str) -> None:
        """Log HTTP response details.

        Args:
            method: HTTP method (GET, POST, PUT, etc.).
            endpoint: API endpoint path.
            status_code: HTTP status code.
            request_id: Unique request identifier.
        """
        if self._enable_logging:
            logger.debug(
                f"Response {status_code}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "endpoint": endpoint,
                    "status": status_code,
                },
            )

    @abstractmethod
    def close(self) -> None:
        """Close and cleanup resources."""
        pass
