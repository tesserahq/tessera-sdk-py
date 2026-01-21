# Tessera SDK Clients

This document describes the available clients in the Tessera SDK and their usage.

## Overview

The Tessera SDK now includes three main clients:

1. **IdentiesClient** - For user authentication and identity management
2. **QuoreClient** - For text summarization and NLP operations
3. **SendlyClient** - For email sending and management

All clients share a common base architecture for consistency and maintainability.

## Architecture

### Base Client

All clients inherit from `BaseClient` which provides:
- HTTP session management
- Common authentication handling
- Standardized error handling
- Configurable timeouts

### Shared Features

- **Authentication**: Bearer token authentication
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

## SendlyClient

### Usage

```python
from tessera_sdk import SendlyClient
from tessera_sdk.sendly.schemas import SendEmailRequest

client = SendlyClient(
    base_url="https://sendly-api.yourdomain.com",
    api_token="your-api-token"
)

# Send an email
request = SendEmailRequest(
    name="Welcome Email",
    tenant_id="your-tenant-id",
    provider_id="your-provider-id",
    from_email="hello@example.com",
    subject="Welcome to our platform!",
    html="<html><body>Hello ${name}! Welcome to ${organizationName}.</body></html>",
    to=["user@example.com"],
    template_variables={
        "name": "John Doe",
        "organizationName": "Acme Corp"
    }
)

result = client.send_email(request)

print(f"Email sent! Status: {result.status}")
print(f"Email ID: {result.id}")
print(f"Sent at: {result.sent_at}")
```

### Available Methods

- `send_email(request: SendEmailRequest)` - Send an email with template variable substitution

### Request/Response Schemas

#### SendEmailRequest
- `name: str` - Name/identifier for the email
- `tenant_id: str` - Tenant identifier
- `provider_id: str` - Provider identifier
- `from_email: str` - Sender email address
- `subject: str` - Email subject line
- `html: str` - HTML content with template variables (e.g., ${variableName})
- `template_variables: Dict[str, Any]` - Variables to replace in the template

#### SendEmailResponse
- `id: str` - Unique identifier for the email record
- `from_email: str` - Sender email address
- `to_email: str` - Recipient email address
- `subject: str` - Email subject line
- `body: str` - Processed email body with variables replaced
- `status: str` - Email status (e.g., 'sent', 'failed')
- `provider_id: str` - Provider identifier
- `provider_message_id: str` - Provider's message identifier
- `tenant_id: str` - Tenant identifier
- `sent_at: datetime` - When the email was sent
- `error_message: str` - Error message if failed (optional)
- `created_at: datetime` - Record creation timestamp
- `updated_at: datetime` - Last update timestamp

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

#### SendlyClient
- `SendlyError`, `SendlyClientError`, etc.

## Configuration

### Common Parameters

All clients support these initialization parameters:

- `base_url: str` - API base URL
- `api_token: str` - Authentication token (optional)
- `timeout: int` - Request timeout in seconds (default: 30)
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
