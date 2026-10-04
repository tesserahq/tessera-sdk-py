# Tessera SDK (Python)

Tessera SDK is a Python client library for integrating Tessera identities into your application. It provides building blocks for authentication middleware and user onboarding flows, plus supporting utilities for Tessera-backed services.

## What it’s for

- Connect your application to Tessera identity services.
- Add authentication middleware and session helpers.
- Support user onboarding flows with SDK primitives.
- Perform live Togly feature checks with service-account authentication and safe,
  configurable fallbacks.

## Getting started

```bash
pip install tessera-sdk
```

![Alt](https://repobeats.axiom.co/api/embed/68fba45681f212f91c97518a7adaf7b815cad452.svg "Repobeats analytics image")

## Managed database transactions

Services let the entry point own the transaction. Each request, task, or
command gets one SQLAlchemy session, which commits on success and rolls back
on error. Repositories and commands never commit.

```python
db_manager = DatabaseManager(database_url, application_name, autoflush=True)
get_db, DbSession = create_db_dependency(db_manager)  # tessera_sdk.server.dependencies

@router.post("/pets")
def create_pet(payload: PetCreate, db: DbSession): ...

with db_manager.session_scope() as db:  # tasks, CLI, event handlers
    ...

on_commit(lambda: publish(event))  # tessera_sdk.infra: runs only after commit
```

See [docs/managed-transactions.md](docs/managed-transactions.md) for the rules,
the adoption steps, and the test and CI helpers in `tessera_sdk.testing`.

## MCP contracts

Services and plugins that expose MCP tools use `tessera_sdk.mcp` for shared event,
diagnostic, metadata, and conformance contracts. See
[docs/mcp-contracts.md](docs/mcp-contracts.md).

## Redis configuration

Redis-backed SDK features prefer `REDIS_URL`. Authenticated deployments should
provide the complete URL as a masked secret, for example:

```text
redis://username:URL_SAFE_PASSWORD@redis:6379/0
```

For compatibility, the SDK falls back to `REDIS_HOST` (default `localhost`) and
`REDIS_PORT` (default `6379`) when `REDIS_URL` is unset. New deployments should
use `REDIS_URL`; host/port configuration is retained only for the legacy
rollout. Redis credentials are never written to application logs by the cache
adapter.
