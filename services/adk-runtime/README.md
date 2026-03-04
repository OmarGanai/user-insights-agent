# Vector ADK Runtime

Python runtime service for Vector draft synthesis.

## Endpoints

- `GET /healthz`
- `POST /synthesize`

## Required Environment

- `GEMINI_API_KEY`
- `GEMINI_MODEL`

`POST /synthesize` expects the request model to match `GEMINI_MODEL`.
