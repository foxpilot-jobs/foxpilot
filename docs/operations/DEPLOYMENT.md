# Deployment

## Baseline

The supported baseline is local execution:

```text
React web/PWA -> FastAPI -> Python services -> SQLite + Ollama
```

This preserves privacy and avoids mandatory hosting costs.

## Local Docker Deployment

Docker Compose packages the API, web app, and PostgreSQL for local web development. Ollama runs on the host by default, which avoids duplicating model downloads and avoids container trust-store problems on enterprise networks. Start host Ollama on a Docker-reachable port.

Terminal 1:

```bash
OLLAMA_HOST=0.0.0.0:11435 ollama serve
```

Terminal 2:

```bash
OLLAMA_HOST=127.0.0.1:11435 ollama pull llama3.1:8b
docker compose up --build -d
```

The API image uses public PyPI. The local Dockerfile includes trusted-host defaults for enterprise TLS proxies that re-sign public traffic. The web image similarly defaults to local npm strict-TLS off for this environment. For a normal deployment, set `NPM_STRICT_SSL=true` and provide the platform's CA bundle rather than disabling certificate verification.

Check services:

```bash
curl http://localhost:8000/api/v1/health/ready
open http://localhost:8080
```

The development PostgreSQL password in Compose is intentionally local-only and must be replaced before any hosted deployment. The optional `container-llm` Compose profile is available for environments with a configured enterprise CA, but host Ollama is the default on macOS.

To run the browser-based local scan against the Compose PostgreSQL instance:

```bash
source .venv/bin/activate
DATABASE_URL=postgresql+psycopg://foxpilot:foxpilot-dev-only@localhost:5432/foxpilot \
OLLAMA_BASE_URL=http://localhost:11435 \
foxpilot scan
```

The scan still runs on the host because it uses the interactive Playwright browser. The API and web app then read the PostgreSQL data.

## Hosted Deployment

Hosted deployment is optional and requires explicit decisions about resume privacy, authentication, data retention, model cost, and source access. The expected shape is:

```text
Static React frontend -> FastAPI service -> PostgreSQL
                                      -> Ollama or optional hosted LLM
```

PostgreSQL replaces SQLite only at the storage boundary. Domain and application services must not be coupled to a specific database.

Set the hosted database explicitly:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/foxpilot
```

Apply schema migrations before starting the API:

```bash
alembic upgrade head
```

The local SQLite path remains the default when `DATABASE_URL` is not set.

## API Protection

Local development leaves API data routes open on localhost. Any non-local deployment must set an explicit authentication mode:

```env
FOXPILOT_ENV=production
FOXPILOT_AUTH_MODE=oidc
FOXPILOT_JWT_ISSUER=https://id.example.com/
FOXPILOT_JWT_AUDIENCE=foxpilot-api
FOXPILOT_JWKS_URL=https://id.example.com/.well-known/jwks.json
```

OIDC clients then send:

```text
Authorization: Bearer <oidc-access-token>
```

Token mode remains available for staging:

```env
FOXPILOT_AUTH_MODE=token
FOXPILOT_API_TOKEN=<long-random-secret>
FOXPILOT_TOKEN_USER_ID=staging-user
```

Token mode is a single shared identity and is not suitable for a public multi-user deployment. OIDC authentication is now available, but hosted production still requires database ownership and per-user data isolation before public launch.

Do not set production mode on the current local web UI yet: the browser client does not have an authentication flow. Use the token guard for protected API clients or staging smoke tests until OIDC is implemented.

## Production Requirements

- Versioned API endpoints.
- OIDC authentication and per-user data isolation.
- TLS at the edge.
- Secret injection through deployment configuration.
- Health and readiness checks.
- Structured logs without resume contents or credentials.
- Database backups and restore verification.
- Rate limits for source adapters and user-triggered scans.
- Explicit consent before hosted LLM processing.
