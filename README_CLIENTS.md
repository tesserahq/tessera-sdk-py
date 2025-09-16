# Tessera SDK Clients

This document describes the available clients in the Tessera SDK and their usage.

## Overview

The Tessera SDK now includes two main clients:

1. **IdentiesClient** - For user authentication and identity management
2. **QuoreClient** - For text summarization and NLP operations

Both clients share a common base architecture for consistency and maintainability.

## Architecture

### Base Client

All clients inherit from `BaseClient` which provides:
- HTTP session management with retry logic
- Common authentication handling
- Standardized error handling
- Configurable timeouts and retry strategies

### Shared Features

- **Authentication**: Bearer token authentication
- **Retry Logic**: Automatic retries for transient failures (429, 5xx status codes)
- **Error Handling**: Standardized exception hierarchy
- **Session Management**: Persistent HTTP sessions with connection pooling

## IdentiesClient

### Usage

```python
from tessera_sdk import IdentiesClient

client = IdentiesClient(
    base_url="https://identies-api.yourdomain.com",
    api_token="your-api-token"
)

# Get user information
user_info = client.userinfo()
print(f"User: {user_info.first_name} {user_info.last_name}")

# Introspect token
result = client.introspect()
print(f"Token active: {result.active}")
```

### Available Methods

- `userinfo()` - Get current user information
- `get_user()` - Get user details
- `introspect()` - Introspect API token

## QuoreClient

### Usage

```python
from tessera_sdk import QuoreClient

client = QuoreClient(
    base_url="http://localhost:8005",
    api_token="your-api-token"
)

# Summarize text
result = client.summarize(
    project_id="your-project-id",
    prompt_id="your-prompt-id",
    text="Long text to summarize...",
    labels={"source": "document", "type": "article"}
)

print(f"Summary: {result.summary}")
print(f"Tokens used: {result.tokens_used}")
```

### Available Methods

- `summarize(project_id, prompt_id, text, labels=None)` - Summarize text using specified prompt

### Request/Response Schemas

#### SummarizeRequest
- `prompt_id: str` - ID of the prompt to use
- `text: str` - Text content to summarize
- `labels: Dict[str, Any]` - Optional metadata labels

#### SummarizeResponse
- `summary: str` - Generated summary
- `prompt_id: str` - Prompt ID used
- `labels: Dict[str, Any]` - Associated labels
- `created_at: datetime` - Creation timestamp
- `tokens_used: int` - Token count

## Error Handling

Both clients use a hierarchical exception system:

### Base Exceptions (from `tessera_sdk.base.exceptions`)
- `TesseraError` - Base exception
- `TesseraClientError` - 4xx HTTP errors
- `TesseraServerError` - 5xx HTTP errors
- `TesseraAuthenticationError` - 401 errors
- `TesseraNotFoundError` - 404 errors
- `TesseraValidationError` - 400 errors

### Client-Specific Exceptions
Each client has its own exception classes that inherit from the base exceptions:

#### IdentiesClient
- `IdentiesError`, `IdentiesClientError`, etc.

#### QuoreClient
- `QuoreError`, `QuoreClientError`, etc.

## Configuration

### Common Parameters

All clients support these initialization parameters:

- `base_url: str` - API base URL
- `api_token: str` - Authentication token (optional)
- `timeout: int` - Request timeout in seconds (default: 30)
- `max_retries: int` - Maximum retry attempts (default: 3)
- `session: requests.Session` - Custom session instance (optional)

### Example with Custom Configuration

```python
import requests
from tessera_sdk import QuoreClient

# Custom session with additional headers
session = requests.Session()
session.headers.update({"Custom-Header": "value"})

client = QuoreClient(
    base_url="http://localhost:8005",
    api_token="your-token",
    timeout=60,
    max_retries=5,
    session=session
)
```

## Development

### Adding New Clients

To add a new client:

1. Create a new directory under `tessera_sdk/`
2. Inherit from `BaseClient`
3. Implement client-specific exceptions inheriting from base exceptions
4. Create request/response schemas using Pydantic
5. Add the client to `tessera_sdk/__init__.py`

### Example Structure

```
tessera_sdk/
├── base/
│   ├── client.py      # BaseClient
│   └── exceptions.py  # Base exceptions
├── your_client/
│   ├── __init__.py
│   ├── client.py      # YourClient(BaseClient)
│   ├── exceptions.py  # Client-specific exceptions
│   └── schemas/
│       └── *.py       # Pydantic models
```
