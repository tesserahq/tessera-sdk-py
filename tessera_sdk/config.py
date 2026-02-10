import json
from pydantic import AliasChoices, Field
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_host: str = Field(
        default="localhost", json_schema_extra={"env": "REDIS_HOST"}
    )
    redis_port: int = Field(default=6379, json_schema_extra={"env": "REDIS_PORT"})
    redis_namespace: str = Field(
        default="llama_index", json_schema_extra={"env": "REDIS_NAMESPACE"}
    )
    identies_api_url: str = Field(
        default="https://identies.tessera.com",
        json_schema_extra={"env": "IDENTIES_API_URL"},
    )
    custos_api_url: str = Field(
        default="https://custos.tessera.com",
        json_schema_extra={"env": "CUSTOS_API_URL"},
    )
    sendly_api_url: str = Field(
        default="https://sendly.tessera.com",
        json_schema_extra={"env": "SENDLY_API_URL"},
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
    oidc_jwks_urls: Optional[str] = Field(
        default=None, json_schema_extra={"env": "OIDC_JWKS_URLS"}
    )
    auth_providers_json: Optional[str] = Field(
        default=None, json_schema_extra={"env": "AUTH_PROVIDERS_JSON"}
    )

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

    def get_oidc_jwks_urls(self) -> list[str]:
        if self.oidc_jwks_urls:
            urls = [v.strip() for v in self.oidc_jwks_urls.split(",") if v.strip()]
        else:
            urls = []
            if self.oidc_domain:
                urls.append(f"https://{self.oidc_domain}/.well-known/jwks.json")
            if self.identies_api_url:
                urls.append(f"{self.identies_api_url}/.well-known/jwks.json")
        return list(dict.fromkeys(urls))

    def get_auth_providers(self) -> list[dict]:
        """
        Return auth providers with jwks_url, issuer, and audiences.
        """
        if self.auth_providers_json:
            providers = json.loads(self.auth_providers_json)
            if not isinstance(providers, list):
                raise ValueError("AUTH_PROVIDERS_JSON must be a list")
            return providers

        jwks_urls = self.get_oidc_jwks_urls()
        if not jwks_urls:
            return []

        return [
            {
                "jwks_url": jwks_urls[0],
                "issuer": self.oidc_issuer,
                "audiences": [self.oidc_api_audience],
            }
        ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra environment variables


def get_settings() -> Settings:
    """Get application settings with required environment variables."""
    return Settings()
