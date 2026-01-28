# Tessera SDK Usage Guide

## Installation

```bash
pip install tessera-sdk
# or
poetry add tessera-sdk
```

## What This SDK Provides

- **IdentiesClient**: For interacting with the Identies API
- **AuthenticationMiddleware**: Handles token validation and API key authentication
- **UserOnboardingMiddleware**: Manages user onboarding independently of authentication
- **Schemas**: Pydantic models for type safety

## Framework Compatibility

The middlewares work with **any ASGI framework**:
- FastAPI
- Starlette
- Quart
- Any other ASGI-compatible framework

**Dependencies**: Only requires `starlette` (no FastAPI required!)

## Basic Usage

### 1. With FastAPI (Most Common)

```python
from fastapi import FastAPI
from tessera_sdk.middleware.authentication import AuthenticationMiddleware
from tessera_sdk.middleware.user_onboarding import UserOnboardingMiddleware
from tessera_sdk.schemas.user import UserServiceInterface, UserOnboard

# Your user service implementation
class MyUserService(UserServiceInterface):
    def onboard_user(self, user_data: UserOnboard):
        # Create user in your database
        return create_user_in_db(user_data)
    
    def get_user_by_external_id(self, external_id: str):
        # Look up user in your database
        return find_user_by_external_id(external_id)

# Create FastAPI app
app = FastAPI()

# Add middlewares (order matters!)
app.add_middleware(
    UserOnboardingMiddleware,
    identies_api_url="https://api.identies.com",
    user_service=MyUserService()
)

app.add_middleware(
    AuthenticationMiddleware,
    identies_api_url="https://api.identies.com"
)

# Your endpoints
@app.get("/protected")
async def protected_endpoint(request):
    user = request.state.user  # Set by middleware
    return {"user_id": user.id, "email": user.email}
```

### 2. With Starlette (Lightweight)

```python
from starlette.applications import Starlette
from starlette.routing import Route
from tessera_sdk.middleware.authentication import AuthenticationMiddleware
from tessera_sdk.middleware.user_onboarding import UserOnboardingMiddleware

async def protected_endpoint(request):
    user = request.state.user
    return {"user_id": user.id}

# Create Starlette app
app = Starlette(routes=[
    Route("/protected", protected_endpoint)
])

# Add middlewares
app.add_middleware(UserOnboardingMiddleware, identies_api_url="https://api.identies.com")
app.add_middleware(AuthenticationMiddleware, identies_api_url="https://api.identies.com")
```

### 3. With Quart (Async Flask-like)

```python
from quart import Quart
from tessera_sdk.middleware.authentication import AuthenticationMiddleware
from tessera_sdk.middleware.user_onboarding import UserOnboardingMiddleware

app = Quart(__name__)

app.add_middleware(UserOnboardingMiddleware, identies_api_url="https://api.identies.com")
app.add_middleware(AuthenticationMiddleware, identies_api_url="https://api.identies.com")

@app.route("/protected")
async def protected_endpoint():
    user = request.state.user
    return {"user_id": user.id}
```

## Authentication Methods

The SDK supports two authentication methods:

### 1. Bearer Token Authentication
```bash
curl -H "Authorization: Bearer your-jwt-token" https://your-api.com/protected
```

### 2. API Key Authentication
```bash
curl -H "X-API-Key: your-api-key" https://your-api.com/protected
```

## User Onboarding Flow

1. **Authentication**: User authenticates with token or API key
2. **User Check**: Middleware checks if user exists locally
3. **Onboarding**: If needed, fetches complete user data from Identies
4. **Local Creation**: Creates user in your local database
5. **Request Processing**: Continues with the authenticated user

## Configuration

### Environment Variables
```bash
export IDENTIES_BASE_URL="https://api.identies.com"
```

### Middleware Parameters

#### AuthenticationMiddleware
- `identies_api_url`: Base URL for Identies API

#### UserOnboardingMiddleware
- `identies_api_url`: Base URL for Identies API
- `user_service`: Your user service implementation (optional)

## Error Handling

The middlewares provide comprehensive error handling:

- **401 Unauthorized**: Invalid or missing token/API key
- **403 Forbidden**: Valid token but insufficient permissions
- **503 Service Unavailable**: Identies API is down
- **500 Internal Error**: Unexpected errors

## Advanced Usage

### Custom User Service

```python
from tessera_sdk.schemas.user import UserServiceInterface, UserOnboard

class CustomUserService(UserServiceInterface):
    def __init__(self, db_connection):
        self.db = db_connection
    
    def onboard_user(self, user_data: UserOnboard):
        # Your custom onboarding logic
        user = self.db.users.create(
            external_id=user_data.external_id,
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            avatar_url=user_data.avatar_url
        )
        return user
    
    def get_user_by_external_id(self, external_id: str):
        return self.db.users.find_by_external_id(external_id)
```

### Custom Onboarding Logic

```python
from tessera_sdk.middleware.user_onboarding import UserOnboardingMiddleware

class CustomUserOnboardingMiddleware(UserOnboardingMiddleware):
    def _user_needs_onboarding(self, user) -> bool:
        # Your custom logic to determine if user needs onboarding
        return not hasattr(user, 'local_id') or user.local_id is None
```

## Testing

```python
from fastapi.testclient import TestClient
from your_app import app

client = TestClient(app)

# Test with API key
response = client.get("/protected", headers={"X-API-Key": "test-key"})
assert response.status_code == 200

# Test with Bearer token
response = client.get("/protected", headers={"Authorization": "Bearer test-token"})
assert response.status_code == 200
```

## Benefits

- **Framework Agnostic**: Works with any ASGI framework
- **Lightweight**: Only requires Starlette, not FastAPI
- **Type Safe**: Full Pydantic model support
- **Comprehensive**: Handles both authentication and onboarding
- **Flexible**: Customizable user service and onboarding logic
- **Production Ready**: Proper error handling and logging
