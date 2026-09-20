import os
import uuid

import pytest
from redis import AuthenticationError, Redis

from tessera_sdk.infra.cache import Cache

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_REDIS_URL"),
    reason="TEST_REDIS_URL is required for Redis ACL integration tests",
)


def test_cache_round_trip_with_named_acl_user(monkeypatch):
    namespace = f"sdk-acl-test:{uuid.uuid4()}"
    monkeypatch.setenv("REDIS_URL", os.environ["TEST_REDIS_URL"])
    cache = Cache(namespace)

    assert cache.write("value", {"authenticated": True}, ttl=30)
    assert cache.read("value") == {"authenticated": True}
    assert 0 < cache.ttl("value") <= 30

    cache.clear_all()


def test_anonymous_redis_access_is_rejected():
    anonymous_url = os.environ["TEST_REDIS_ANONYMOUS_URL"]
    client = Redis.from_url(anonymous_url, socket_connect_timeout=5)

    with pytest.raises(AuthenticationError):
        client.ping()
