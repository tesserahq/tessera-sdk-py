from tessera_sdk.config import Settings


def test_redis_connection_url_prefers_authenticated_url(monkeypatch):
    redis_url = "redis://linden_app:test-password@redis:6379/0"
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("REDIS_HOST", "legacy-redis")
    monkeypatch.setenv("REDIS_PORT", "6380")

    assert Settings(_env_file=None).redis_connection_url == redis_url


def test_redis_connection_url_falls_back_to_legacy_host_and_port(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("REDIS_HOST", "legacy-redis")
    monkeypatch.setenv("REDIS_PORT", "6380")

    assert Settings(_env_file=None).redis_connection_url == (
        "redis://legacy-redis:6380/0"
    )
