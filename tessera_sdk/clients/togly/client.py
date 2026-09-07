"""Client for Togly runtime feature checks."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Protocol
from urllib.parse import quote

import requests
from pydantic import ValidationError

from ...config import get_settings
from ...constants import HTTPMethods
from .._base.client import BaseClient
from .._base.exceptions import (
    TesseraAuthenticationError,
    TesseraClientError,
    TesseraError,
    TesseraNotFoundError,
    TesseraServerError,
    TesseraValidationError,
)
from .schemas import EnabledFeaturesResponse, FeatureCheckResponse

logger = logging.getLogger(__name__)


class TokenProvider(Protocol):
    """The AuthTokenProvider interface used by ToglyClient."""

    def get_token(self) -> str: ...


class ToglyClient(BaseClient):
    """Thin, synchronous client for Togly feature-check endpoints.

    Feature decisions are always made by Togly. This client intentionally does
    not cache feature results or implement gate logic.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        timeout: float | None = None,
        session: requests.Session | None = None,
        auth_token_provider: TokenProvider | None = None,
        audience: str | None = None,
    ):
        if api_token is not None and auth_token_provider is not None:
            raise ValueError("Provide api_token or auth_token_provider, not both")

        settings = get_settings()
        resolved_base_url = base_url or settings.togly_api_url
        resolved_timeout = (
            timeout
            if timeout is not None
            else settings.tesserasdk_togly_client_timeout
        )

        if api_token is None and auth_token_provider is None:
            # Imported lazily to avoid a clients -> infra -> clients cycle while
            # tessera_sdk.clients is being initialized.
            from ...infra.auth_token_provider import AuthTokenProvider

            auth_token_provider = AuthTokenProvider(
                audience=audience or settings.togly_api_audience
            )

        self.auth_token_provider = auth_token_provider
        super().__init__(
            base_url=resolved_base_url,
            api_token=api_token,
            timeout=resolved_timeout,
            session=session,
            service_name="togly",
        )

    def is_enabled(
        self,
        feature_key: str,
        *,
        actor_id: str | None = None,
        default: bool = False,
    ) -> bool:
        """Return whether a feature is enabled for an actor.

        When actor_id is omitted, Togly checks only the global boolean gate.
        Transport failures and Togly 5xx responses return default. Authentication,
        authorization, validation, and other 4xx failures remain visible.
        """
        endpoint = f"/feature-checks/{quote(feature_key, safe='')}"
        params = {"actor_id": actor_id} if actor_id is not None else None

        try:
            response = self._make_request(
                HTTPMethods.GET,
                endpoint,
                params=params,
                headers=self._authorization_headers(),
            )
        except TesseraServerError:
            self._log_fallback("feature check", feature_key)
            return default
        except (
            TesseraAuthenticationError,
            TesseraClientError,
            TesseraNotFoundError,
            TesseraValidationError,
        ):
            raise
        except (TesseraError, requests.exceptions.RequestException):
            self._log_fallback("feature check", feature_key)
            return default

        try:
            return FeatureCheckResponse.model_validate(response.json()).enabled
        except (ValueError, ValidationError) as exc:
            raise TesseraClientError(
                f"[ToglyClient] {endpoint}: invalid response payload"
            ) from exc

    def enabled_features(
        self,
        *,
        actor_id: str | None = None,
        default: Sequence[str] | None = None,
    ) -> list[str]:
        """Return only feature keys enabled for an actor.

        When actor_id is omitted, Togly returns globally enabled feature keys.
        Transport failures and Togly 5xx responses return a copy of default, or
        an empty list when no default is supplied.
        """
        fallback = list(default) if default is not None else []
        params = {"actor_id": actor_id} if actor_id is not None else None

        try:
            response = self._make_request(
                HTTPMethods.GET,
                "/enabled-features",
                params=params,
                headers=self._authorization_headers(),
            )
        except TesseraServerError:
            self._log_fallback("enabled-features query")
            return fallback
        except (
            TesseraAuthenticationError,
            TesseraClientError,
            TesseraNotFoundError,
            TesseraValidationError,
        ):
            raise
        except (TesseraError, requests.exceptions.RequestException):
            self._log_fallback("enabled-features query")
            return fallback

        try:
            payload = EnabledFeaturesResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise TesseraClientError(
                "[ToglyClient] /enabled-features: invalid response payload"
            ) from exc
        return payload.features

    def _authorization_headers(self) -> dict[str, str] | None:
        if self.auth_token_provider is None:
            return None
        return {"Authorization": f"Bearer {self.auth_token_provider.get_token()}"}

    @staticmethod
    def _log_fallback(operation: str, feature_key: str | None = None) -> None:
        context = f" for feature {feature_key!r}" if feature_key else ""
        logger.warning(
            "Togly %s failed%s; returning the caller fallback",
            operation,
            context,
        )
