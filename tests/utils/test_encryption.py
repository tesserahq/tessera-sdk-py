import pytest

from tessera_sdk.utils import encryption


def test_get_encryption_key_requires_env(monkeypatch):
    monkeypatch.delenv("MASTER_SECRET_KEY", raising=False)

    with pytest.raises(ValueError):
        encryption.get_encryption_key()


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setenv("MASTER_SECRET_KEY", "secret")

    payload = {"name": "Ada", "role": "engineer"}
    encrypted = encryption.encrypt_data(payload)

    assert encrypted is not None
    assert encryption.decrypt_data(encrypted) == payload


def test_encrypt_returns_none_for_empty(monkeypatch):
    monkeypatch.setenv("MASTER_SECRET_KEY", "secret")

    assert encryption.encrypt_data({}) is None


def test_decrypt_returns_none_for_empty(monkeypatch):
    monkeypatch.setenv("MASTER_SECRET_KEY", "secret")

    assert encryption.decrypt_data("") is None


def test_decrypt_invalid_payload_raises(monkeypatch):
    monkeypatch.setenv("MASTER_SECRET_KEY", "secret")

    with pytest.raises(ValueError):
        encryption.decrypt_data("not-encrypted")
