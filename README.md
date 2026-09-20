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
