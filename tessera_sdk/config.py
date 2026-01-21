import os
from pydantic import AliasChoices, Field, model_validator
from typing import Optional
from pydantic_settings import BaseSettings
from sqlalchemy.engine.url import make_url, URL


class Settings(BaseSettings):
    redis_host: str = Field(
        default="localhost", json_schema_extra={"env": "REDIS_HOST"}
    )
    redis_port: int = Field(default=6379, json_schema_extra={"env": "REDIS_PORT"})
    redis_namespace: str = Field(
        default="llama_index", json_schema_extra={"env": "REDIS_NAMESPACE"}
    )
    identies_base_url: str = Field(
        default="https://identies.tessera.com",
        json_schema_extra={"env": "IDENTIES_BASE_URL"},
    )
    custos_api_url: str = Field(
        default="https://custos.tessera.com",
        json_schema_extra={"env": "CUSTOS_API_URL"},
    )
    authorization_cache_enabled: bool = Field(
        default=False,
        json_schema_extra={"env": "AUTHORIZATION_CACHE_ENABLED"},
    )
    authorization_cache_ttl: int = Field(
        default=300,
        json_schema_extra={"env": "AUTHORIZATION_CACHE_TTL"},
    )
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENV", "ENVIRONMENT"),
    )
    log_level: str = Field(default="INFO", json_schema_extra={"env": "LOG_LEVEL"})
    disable_auth: bool = Field(default=False, json_schema_extra={"env": "DISABLE_AUTH"})
    port: int = Field(default=8000, json_schema_extra={"env": "PORT"})
    identies_host: Optional[str] = Field(
        default=None,
        json_schema_extra={"env": "IDENTIES_HOST"},
    )

    # Tessera SDK (namespaced) settings
    tesserasdk_base_client_timeout: int = Field(
        default=3,
        validation_alias=AliasChoices(
            "TESSERA_BASE_CLIENT_TIMEOUT",
            "TESSERASDK_BASE_CLIENT_TIMEOUT",
            "tesserasdk.base_client.timeout",
        ),
    )

    tesserasdk_auth_middleware_timeout: int = Field(
        default=3,
        validation_alias=AliasChoices(
            "TESSERASDK_AUTH_MIDDLEWARE_TIMEOUT",
            "tesserasdk.auth_middleware.timeout",
        ),
    )

    oidc_domain: str = "test.oidc.com"
    oidc_api_audience: str = "https://test-api"
    oidc_issuer: str = "https://test.oidc.com/"
    oidc_algorithms: str = "RS256"

    service_account_client_id: str = Field(
        default="", json_schema_extra={"env": "SERVICE_ACCOUNT_CLIENT_ID"}
    )
    service_account_client_secret: str = Field(
        default="", json_schema_extra={"env": "SERVICE_ACCOUNT_CLIENT_SECRET"}
    )
    nats_enabled: bool = Field(default=False, json_schema_extra={"env": "NATS_ENABLED"})
    nats_url: str = Field(
        default="nats://localhost:4222", json_schema_extra={"env": "NATS_URL"}
    )
    event_type_prefix: str = Field(
        default="com.mylinden", json_schema_extra={"env": "EVENT_TYPE_PREFIX"}
    )
    event_source_prefix: str = Field(
        default="linden-api", json_schema_extra={"env": "EVENT_SOURCE_PREFIX"}
    )

    @property
    def is_production(self) -> bool:
        """Check if the current environment is production."""
        return self.environment.lower() == "production"

    @property
    def is_test(self) -> bool:
        """Check if the current environment is test."""
        return self.environment.lower() == "test"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra environment variables


def get_settings() -> Settings:
    """Get application settings with required environment variables."""
    return Settings()
