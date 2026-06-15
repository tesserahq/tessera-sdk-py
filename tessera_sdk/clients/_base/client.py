"""
Base client class for all Tessera SDK clients.
"""

import logging
from typing import Optional, Dict, Any
import requests

from ...config import get_settings
from .exceptions import (
    TesseraError,
    TesseraClientError,
    TesseraServerError,
    TesseraAuthenticationError,
    TesseraNotFoundError,
    TesseraValidationError,
)

logger = logging.getLogger(__name__)


class BaseClient:
    """
    Base client class for interacting with Tessera APIs.

    This class provides common functionality for all API clients including
    HTTP session management and error handling.
    """

    def __init__(
        self,
        base_url: str,
        api_token: Optional[str] = None,
        timeout: Optional[int] = None,
        session: Optional[requests.Session] = None,
        service_name: str = "tessera",
    ):
        """
        Initialize the base client.

        Args:
            base_url: The base URL of the API (e.g., "https://api.yourdomain.com")
            api_token: Optional API token for authentication
            timeout: Request timeout in seconds
            session: Optional requests.Session instance to use
            service_name: Name of the service for User-Agent header
        """
        settings = get_settings()

        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = (
            int(timeout)
            if timeout is not None
            else int(settings.tesserasdk_base_client_timeout)
        )
        self.service_name = service_name

        # Create or use provided session
        self.session = session or requests.Session()

        # Set default headers
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": f"{service_name}-client/{self._get_version()}",
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
            from ... import __version__

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
        Make an HTTP request to the API.

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
            TesseraClientError: For 4xx status codes
            TesseraServerError: For 5xx status codes
            TesseraError: For other errors
        """
        url = f"{self.base_url}{endpoint}"

        logger.info(f"Making {method} request to {url}")

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
            class_name = self.__class__.__name__
            if response.status_code < 400:
                return response
            elif response.status_code == 401:
                try:
                    detail = response.json().get("detail", "Authentication failed")
                except (ValueError, KeyError):
                    detail = "Authentication failed"
                raise TesseraAuthenticationError(f"[{class_name}] {endpoint}: {detail}")
            elif response.status_code == 404:
                try:
                    detail = response.json().get("detail", "Resource not found")
                except (ValueError, KeyError):
                    detail = "Resource not found"
                raise TesseraNotFoundError(f"[{class_name}] {endpoint}: {detail}")
            elif response.status_code == 400:
                try:
                    detail = response.json().get("detail", "Bad request")
                except (ValueError, KeyError):
                    detail = "Bad request"
                raise TesseraValidationError(f"[{class_name}] {endpoint}: {detail}")
            elif 400 <= response.status_code < 500:
                try:
                    detail = response.json().get(
                        "detail", response.text or "Client error"
                    )
                except (ValueError, KeyError):
                    detail = response.text or "Client error"
                raise TesseraClientError(
                    f"[{class_name}] {endpoint}: {response.status_code} {detail}",
                    response.status_code,
                )
            elif 500 <= response.status_code < 600:
                logger.error(
                    "[%s] Server error %s\nURL: %s\nResponse body: %s",
                    class_name,
                    response.status_code,
                    response.url,
                    response.text,
                )
                raise TesseraServerError(
                    f"[{class_name}] Server error: {response.status_code}",
                    response.status_code,
                )
            else:
                raise TesseraError(
                    f"[{class_name}] Unexpected status code: {response.status_code}"
                )

        except requests.exceptions.RequestException as e:
            class_name = self.__class__.__name__
            logger.exception(
                "[%s] HTTP request failed\nMethod: %s\nURL: %s",
                class_name,
                method,
                url,
            )
            raise TesseraError(f"[{class_name}] {method} {url} failed: {e}") from e
