"""
Main Identies client for interacting with the Identies API.
"""

import logging
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .schemas.introspect_response import IntrospectResponse
from .schemas.user_response import UserResponse
from ..constants import HTTPMethods

from .exceptions import (
    IdentiesError,
    IdentiesClientError,
    IdentiesServerError,
    IdentiesAuthenticationError,
    IdentiesNotFoundError,
    IdentiesValidationError,
)

logger = logging.getLogger(__name__)


class IdentiesClient:
    """
    A client for interacting with the Identies API.

    This client provides methods for managing clients and assets through the Vaulta API.
    """

    def __init__(
        self,
        base_url: str,
        api_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        session: Optional[requests.Session] = None,
    ):
        """
        Initialize the Identies client.

        Args:
            base_url: The base URL of the Identies API (e.g., "https://identies-api.yourdomain.com")
            api_token: Optional API token for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            session: Optional requests.Session instance to use
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout

        # Create or use provided session
        self.session = session or requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=HTTPMethods.ALL_METHODS,
            backoff_factor=1,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": f"identies-client/{self._get_version()}",
            }
        )

        if api_token:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {api_token}",
                }
            )

    def _get_version(self) -> str:
        """Get the client version."""
        try:
            from . import __version__

            return __version__
        except ImportError:
            return "unknown"

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """
        Make an HTTP request to the Identies API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path (e.g., "/clients")
            data: Request data for JSON requests
            files: Files for multipart requests
            params: Query parameters
            headers: Additional headers

        Returns:
            requests.Response object

        Raises:
            IdentiesClientError: For 4xx status codes
            IdentiesServerError: For 5xx status codes
            IdentiesError: For other errors
        """
        url = f"{self.base_url}{endpoint}"

        request_headers = {}
        if headers:
            request_headers.update(headers)

        try:
            if files:
                # For file uploads, don't set Content-Type header
                if "Content-Type" in request_headers:
                    del request_headers["Content-Type"]
                response = self.session.request(
                    method=method,
                    url=url,
                    data=data,
                    files=files,
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout,
                )
            else:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout,
                )

            # Handle different status codes
            if response.status_code < 400:
                return response
            elif response.status_code == 401:
                raise IdentiesAuthenticationError("Authentication failed")
            elif response.status_code == 404:
                raise IdentiesNotFoundError("Resource not found")
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", "Bad request")
                except (ValueError, KeyError):
                    detail = "Bad request"
                raise IdentiesValidationError(detail)
            elif 400 <= response.status_code < 500:
                raise IdentiesClientError(
                    f"Client error: {response.status_code}",
                    response.status_code,
                )
            elif 500 <= response.status_code < 600:
                raise IdentiesServerError(
                    f"Server error: {response.status_code}",
                    response.status_code,
                )
            else:
                raise IdentiesError(f"Unexpected status code: {response.status_code}")

        except requests.exceptions.RequestException as e:
            raise IdentiesError(f"Request failed: {str(e)}")

    # User Management Methods

    def userinfo(self) -> UserResponse:
        """
        Get the user info.

        Args:
            None

        Returns:
            UserInfo object
        """
        response = self._make_request(HTTPMethods.GET, "/userinfo")
        return UserResponse(**response.json())

    def get_user(self) -> UserResponse:
        """
        Get a specific user.

        Args:
            None

        Returns:
            UserResponse object

        Raises:
            IdentiesNotFoundError: If client is not found
        """
        response = self._make_request(HTTPMethods.GET, "/user")
        return UserResponse(**response.json())

    def introspect(self) -> IntrospectResponse:
        """
        Introspect a token.

        Args:
            None

        Returns:
            IntrospectResponse object

        Raises:
            IdentiesNotFoundError: If client is not found
        """
        response = self._make_request(HTTPMethods.POST, "/api-keys/introspect")
        return IntrospectResponse(**response.json())
