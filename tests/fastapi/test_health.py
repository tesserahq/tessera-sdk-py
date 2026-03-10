"""Tests for livez/readyz health endpoints."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tessera_sdk.fastapi import get_livez_readyz_router


def test_livez_returns_200_and_ok():
    """GET /livez returns 200 with status OK."""
    app = FastAPI()
    app.include_router(get_livez_readyz_router())
    client = TestClient(app)

    response = client.get("/livez")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


def test_readyz_without_probes_returns_200_and_ok():
    """GET /readyz without probes returns 200 with status OK."""
    app = FastAPI()
    app.include_router(get_livez_readyz_router())
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


def test_readyz_with_passing_probes_returns_200():
    """GET /readyz with all probes passing returns 200."""

    async def passing_probe():
        return {"ok": True}

    app = FastAPI()
    app.include_router(get_livez_readyz_router(ready_probes=[passing_probe]))
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


def test_readyz_with_failing_probe_returns_503():
    """GET /readyz with a failing probe returns 503."""

    async def failing_probe():
        return {"ok": False, "error": "Database unreachable"}

    app = FastAPI()
    app.include_router(get_livez_readyz_router(ready_probes=[failing_probe]))
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 503
    assert "Database unreachable" in response.json().get("detail", "")


def test_readyz_first_probe_fails_second_not_called():
    """GET /readyz stops at first failing probe."""
    call_order = []

    async def first_probe():
        call_order.append("first")
        return {"ok": False, "error": "First failed"}

    async def second_probe():
        call_order.append("second")
        return {"ok": True}

    app = FastAPI()
    app.include_router(
        get_livez_readyz_router(ready_probes=[first_probe, second_probe])
    )
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 503
    assert call_order == ["first"]


def test_readyz_all_probes_pass_returns_200():
    """GET /readyz with multiple passing probes returns 200."""

    async def probe_a():
        return {"ok": True}

    async def probe_b():
        return {"ok": True}

    app = FastAPI()
    app.include_router(get_livez_readyz_router(ready_probes=[probe_a, probe_b]))
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}
