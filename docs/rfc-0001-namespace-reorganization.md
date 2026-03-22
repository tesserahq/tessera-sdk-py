# RFC-0001: Namespace Reorganization

**Status:** Proposed
**Created:** 2026-03-22

---

## Problem

The `tessera_sdk` root currently mixes two unrelated concerns: external API clients (`identies/`, `custos/`, `vaulta/`, `sendly/`, `quore/`) sit as top-level siblings of infrastructure (`core/`, `utils/`), server middleware (`middleware/`, `auth/`, `fastapi/`), and domain types (`models/`, `schemas/`). There is no structural signal about what layer something belongs to or what it depends on.

Specific symptoms:
- Opening `tessera_sdk/` gives no information about which modules are for callers vs. internal plumbing.
- `utils/` is a grab-bag that mixes server-side request handling (`auth.py`, `authorization_dependency.py`) with infrastructure adapters (`cache.py`, `encryption.py`, `m2m_token.py`) and a template engine (`expressions/`).
- `auth/` handlers (`TokenHandler`, `APIKeyHandler`) instantiate `IdentiesClient` internally, making them untestable without HTTP and creating a hidden upward dependency.
- `base/exceptions.py` imports `fastapi.HTTPException`, polluting the base client layer with a server framework dependency.
- Session header mutation in auth handlers (`session.headers.update(...)`) is not thread-safe under concurrent async requests.

---

## Proposal

Reorganize the package into four named namespaces reflecting actual layers, fix the two structural bugs uncovered during the audit, and provide ergonomic top-level re-exports for the most common import patterns.

This is a two-phase plan.

---

## Phase 1 — Physical Reorganization

### Target Structure

```
tessera_sdk/
├── __init__.py           # Top-level re-exports for common patterns
├── config.py             # Unchanged — global singleton, no internal deps
│
├── clients/              # External API clients (HTTP only, no framework deps)
│   ├── __init__.py
│   ├── _base/
│   │   ├── client.py           # BaseClient (moved from base/)
│   │   └── exceptions.py       # TesseraError hierarchy (pure Python)
│   ├── identies/               # (moved from root)
│   ├── custos/                 # (moved from root)
│   ├── vaulta/                 # (moved from root)
│   ├── sendly/                 # (moved from root)
│   └── quore/                  # (moved from root)
│
├── server/               # Everything that runs inside a FastAPI request lifecycle
│   ├── __init__.py
│   ├── exceptions.py           # UnauthorizedException, UnauthenticatedException
│   ├── auth/
│   │   ├── auth_handler.py     # (moved from auth/)
│   │   ├── api_key_handler.py  # (moved from auth/)
│   │   └── token_handler.py    # (moved from auth/)
│   ├── middleware/
│   │   ├── authentication.py   # (moved from middleware/)
│   │   └── user_onboarding.py  # (moved from middleware/)
│   ├── dependencies/
│   │   ├── auth.py             # get_current_user (moved from utils/auth.py)
│   │   └── authorization.py    # authorize() factory (moved from utils/authorization_dependency.py)
│   └── health.py               # get_livez_readyz_router (moved from fastapi/health.py)
│
├── infra/                # Infrastructure adapters (Redis, DB, NATS, OAuth, crypto)
│   ├── __init__.py
│   ├── cache.py                # (moved from utils/cache.py)
│   ├── database.py             # DatabaseManager (moved from core/database_manager.py)
│   ├── encryption.py           # (moved from utils/encryption.py)
│   ├── encrypted_types.py      # EncryptedJSONB (moved from models/encrypted_types.py)
│   ├── m2m_token.py            # M2MTokenClient (moved from utils/m2m_token.py)
│   ├── service_factory.py      # (moved from utils/service_factory.py)
│   ├── expressions/            # (moved from utils/expressions/)
│   │   ├── engine.py
│   │   └── soft_undefined.py
│   └── events/                 # (moved from events/)
│       ├── event.py
│       ├── nats_router.py
│       └── nats_healthcheck.py
│
└── domain/               # Shared data contracts — no framework or infra deps
    ├── __init__.py
    ├── models/
    │   └── user.py             # UserMixin (moved from models/user.py)
    └── schemas/
        └── user.py             # UserNeedsOnboarding, UserOnboard, UserServiceInterface
```

### Top-Level Exports

`tessera_sdk/__init__.py` re-exports the things every service needs on day 1 so the most common patterns stay as 1-line imports:

```python
# tessera_sdk/__init__.py
from .server import (
    AuthenticationMiddleware,
    UserOnboardingMiddleware,
    get_current_user,
    authorize,
    get_livez_readyz_router,
)
from .infra import DatabaseManager, ServiceFactory
from .clients import (
    IdentiesClient, CustosClient, VaultaClient, SendlyClient, QuoreClient,
)
from .clients._base.exceptions import (
    TesseraError, TesseraAuthenticationError, TesseraNotFoundError,
    TesseraClientError, TesseraServerError, TesseraValidationError,
)
```

Each client's `__init__.py` re-exports its own schemas so callers don't need to know about the `schemas/` subdirectory:

```python
# clients/sendly/__init__.py
from .client import SendlyClient
from .exceptions import SendlyError, SendlyClientError, SendlyServerError
from .schemas import CreateEmailRequest, CreateEmailResponse
```

### Caller Import — Before vs. After

```python
# BEFORE
from tessera_sdk.middleware.authentication import AuthenticationMiddleware
from tessera_sdk.middleware.user_onboarding import UserOnboardingMiddleware
from tessera_sdk.utils.auth import get_current_user
from tessera_sdk.utils.authorization_dependency import authorize
from tessera_sdk.fastapi.health import get_livez_readyz_router
from tessera_sdk.core.database_manager import DatabaseManager
from tessera_sdk.utils.service_factory import ServiceFactory
from tessera_sdk.utils.cache import Cache
from tessera_sdk.events.event import Event, event_type, event_source
from tessera_sdk.events.nats_router import NatsEventPublisher
from tessera_sdk.models import UserMixin
from tessera_sdk.sendly.schemas.create_email_request import CreateEmailRequest

# AFTER
from tessera_sdk import AuthenticationMiddleware, UserOnboardingMiddleware
from tessera_sdk import get_current_user, authorize, get_livez_readyz_router
from tessera_sdk import DatabaseManager, ServiceFactory
from tessera_sdk.infra import Cache
from tessera_sdk.infra.events import Event, event_type, event_source, NatsEventPublisher
from tessera_sdk.domain import UserMixin
from tessera_sdk.clients.sendly import SendlyClient, CreateEmailRequest
```

### Backward Compatibility

Old import paths are preserved as re-export shims with deprecation warnings for one release cycle:

```python
# tessera_sdk/middleware/authentication.py  (shim)
import warnings
warnings.warn(
    "Import from tessera_sdk.server.middleware.authentication instead.",
    DeprecationWarning,
    stacklevel=2,
)
from tessera_sdk.server.middleware.authentication import AuthenticationMiddleware
```

---

## Phase 2 — Fix Structural Bugs

These are independent of Phase 1 but discovered during the audit. They can land in the same PR or a follow-up.

### Bug 1: `base/exceptions.py` imports FastAPI

`TesseraError`, `TesseraClientError`, etc. are pure Python exceptions but `base/exceptions.py` currently imports `fastapi.HTTPException` to define `UnauthorizedException` and `UnauthenticatedException`. This pulls FastAPI into the client layer import chain, breaking the goal of framework-agnostic clients.

**Fix:** Split the file.
- Pure `TesseraError` hierarchy → `clients/_base/exceptions.py`
- `UnauthorizedException`, `UnauthenticatedException` → `server/exceptions.py`

### Bug 2: Auth handlers couple to `IdentiesClient` internally

`TokenHandler.__init__` and `APIKeyHandler.__init__` both call `IdentiesClient(...)` directly. This makes them impossible to unit-test without live HTTP and creates a hidden dependency from the server layer into the clients layer via direct instantiation.

Additionally, both handlers mutate `identies_client.session.headers` to inject a per-request Bearer token. This is not thread-safe under concurrent async requests.

**Fix:** Introduce a minimal `IntrospectPort` protocol and inject via constructor:

```python
# server/auth/protocols.py
from typing import Protocol
from tessera_sdk.clients.identies.schemas import IntrospectResponse, UserResponse

class IntrospectPort(Protocol):
    def introspect(self, bearer_token: str) -> IntrospectResponse: ...

class UserInfoPort(Protocol):
    def userinfo(self, bearer_token: str) -> UserResponse: ...
```

```python
# server/auth/token_handler.py
class TokenHandler:
    def __init__(self, introspect_port: IntrospectPort):
        self._introspect = introspect_port
        # no IdentiesClient import, no session header mutation
```

```python
# Wiring happens once at app startup
from tessera_sdk.clients.identies import IdentiesClient
from tessera_sdk.server.auth import build_auth_handlers

api_key_handler, token_handler = build_auth_handlers(settings)
app.add_middleware(
    AuthenticationMiddleware,
    api_key_handler=api_key_handler,
    token_handler=token_handler,
)
```

`IdentiesClient` gains per-call token methods (`introspect(bearer_token=...)`) so the mutation pattern is eliminated entirely.

---

## Layer Dependency Rules

After both phases, the allowed import directions are:

```
config.py         (no internal imports)
    ↓
domain/           (stdlib + pydantic + sqlalchemy only)
    ↓
infra/            (domain + config)
    ↓
clients/          (domain + config)
    ↓
server/           (clients + infra + domain + config)
    ↓
__init__.py       (re-exports only)
```

No layer may import from a layer above it. `server/` is the only layer that imports from `clients/` — and only for wiring (e.g., `build_auth_handlers` constructing a concrete `IdentiesClient` to inject).

---

## Files Affected

### Moved (no content changes)
- `base/` → `clients/_base/`
- `identies/`, `custos/`, `vaulta/`, `sendly/`, `quore/` → `clients/`
- `auth/` → `server/auth/`
- `middleware/` → `server/middleware/`
- `fastapi/` → `server/health.py`
- `utils/auth.py` → `server/dependencies/auth.py`
- `utils/authorization_dependency.py` → `server/dependencies/authorization.py`
- `utils/cache.py` → `infra/cache.py`
- `utils/encryption.py` → `infra/encryption.py`
- `utils/m2m_token.py` → `infra/m2m_token.py`
- `utils/service_factory.py` → `infra/service_factory.py`
- `utils/expressions/` → `infra/expressions/`
- `core/database_manager.py` → `infra/database.py`
- `events/` → `infra/events/`
- `models/user.py` → `domain/models/user.py`
- `models/encrypted_types.py` → `infra/encrypted_types.py`
- `schemas/` → `domain/schemas/`
- `constants/` → `clients/_base/constants/` (or keep at root — low priority)

### Modified (content changes)
- `tessera_sdk/__init__.py` — new top-level re-exports
- All internal relative imports updated to reflect new paths
- `base/exceptions.py` → split into `clients/_base/exceptions.py` + `server/exceptions.py` (Phase 2)
- `auth/token_handler.py`, `auth/api_key_handler.py` → accept `IntrospectPort` via constructor (Phase 2)

### Added (new files)
- `clients/__init__.py`, `server/__init__.py`, `infra/__init__.py`, `domain/__init__.py`
- `server/auth/protocols.py` (Phase 2)
- Deprecation shims at all old paths

### Deleted (after deprecation period)
- `base/`, `auth/`, `middleware/`, `fastapi/`, `core/`, `utils/`, `events/`, `models/`, `schemas/` (original locations)

---

## Open Questions

1. Should `constants/http_methods.py` move into `clients/_base/` (since only clients use it) or stay at the root?
2. Should `M2MTokenClient` live in `infra/` (it's a network client but uses `BaseClient`) or `server/dependencies/` (it's used for server-side credential fetching)? Current recommendation: `infra/` with a deliberate documented exception allowing `infra/` to import `clients/_base/client.py`.
3. Migration timeline: one release with deprecation shims, or a single breaking version bump?
