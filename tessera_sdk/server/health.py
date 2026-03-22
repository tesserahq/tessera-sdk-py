"""
Kubernetes-style health check endpoints for FastAPI.

Provides /livez and /readyz endpoints suitable for container orchestration
(e.g., Kubernetes liveness and readiness probes).
"""

from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response model for health check endpoints."""

    status: str = "OK"


def get_livez_readyz_router(
    ready_probes: list[Callable[[], Awaitable[dict]]] | None = None,
) -> APIRouter:
    """
    Return an APIRouter with /livez and /readyz endpoints.

    Args:
        ready_probes: Optional list of async callables that return a dict with
            "ok" (bool) and optional "error" (str). If any probe returns ok=False,
            /readyz returns 503.

    Returns:
        APIRouter with /livez and /readyz routes.

    Example:
        >>> from tessera_sdk.fastapi import get_livez_readyz_router
        >>> app.include_router(get_livez_readyz_router())
    """
    router = APIRouter(tags=["health"])

    @router.get(
        "/livez",
        response_model=HealthResponse,
        status_code=status.HTTP_200_OK,
        summary="Liveness probe",
        description="""
Use this endpoint to determine if the API server should be restarted.

If `/livez` returns a failure status code (such as 500), the API server is
likely in a non-recoverable state, such as a deadlock, and requires a restart.

This endpoint performs a minimal check: if the process can respond to the
request, it returns 200 OK. If the process is deadlocked or otherwise
unresponsive, the request will fail or timeout.
        """.strip(),
        response_description="Returns HTTP 200 OK if the process is alive",
    )
    async def livez() -> HealthResponse:
        """Liveness probe: returns OK if the process can respond."""
        return HealthResponse(status="OK")

    @router.get(
        "/readyz",
        response_model=HealthResponse,
        status_code=status.HTTP_200_OK,
        summary="Readiness probe",
        description="""
Use this endpoint to determine if the API server is ready to accept traffic.

If `/readyz` returns a failure status code (e.g. 503), it indicates the server
is still initializing or temporarily unable to serve requests (for example,
waiting for the database or message bus to be available). Traffic should be
routed away from the instance until it becomes ready.

When no readiness probes are configured, this endpoint returns 200 OK.
When probes are provided via `get_livez_readyz_router(ready_probes=[...])`,
all probes must pass for the endpoint to return 200.
        """.strip(),
        response_description="Returns HTTP 200 OK if the server is ready to accept traffic",
    )
    async def readyz() -> HealthResponse:
        """Readiness probe: returns OK if the server is ready to accept traffic."""
        if ready_probes:
            for probe in ready_probes:
                result = await probe()
                if not result.get("ok", True):
                    detail = result.get("error", "Readiness check failed")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=detail,
                    )
        return HealthResponse(status="OK")

    return router
