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
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

Terminal 2:

```bash
OLLAMA_HOST=127.0.0.1:11434 ollama pull llama3.1:8b
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
OLLAMA_BASE_URL=http://localhost:11434 \
foxpilot scan
```

For Google sign-in, configure `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and an exact `GOOGLE_REDIRECT_URI` matching the Google Cloud OAuth client. Never expose the client secret to the frontend.

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

Local development leaves API data routes open on localhost and uses the explicit `local-user` identity. Token mode remains available as a temporary single-user staging guard:

```env
FOXPILOT_AUTH_MODE=token
FOXPILOT_API_TOKEN=<long-random-secret>
FOXPILOT_TOKEN_USER_ID=staging-user
```

Token mode is not suitable for public multi-user deployment. Hosted production will use native FoxPilot authentication with branded registration, secure password hashing, HTTP-only sessions, email verification, and password recovery.

Enable the current native session flow with:

```env
FOXPILOT_ENV=production
FOXPILOT_AUTH_MODE=native
```

For local browser testing, keep `FOXPILOT_ENV=local` so cookies do not require HTTPS. Set `FOXPILOT_AUTH_MODE=local` to return to the private single-user dashboard.

Production native registration requires SMTP configuration for verification and password recovery:

```env
EMAIL_FROM=FoxPilot <accounts@example.com>
EMAIL_SMTP_HOST=smtp.example.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME=accounts@example.com
EMAIL_SMTP_PASSWORD=<secret>
EMAIL_SMTP_TLS=true
FOXPILOT_PUBLIC_URL=https://foxpilot.example.com
```

## Production Requirements

- Versioned API endpoints.
- Native FoxPilot authentication and per-user data isolation.
- TLS at the edge.
- Secret injection through deployment configuration.
- Health and readiness checks.
- Structured logs without resume contents or credentials.
- Database backups and restore verification.
- Rate limits for source adapters and user-triggered scans.
- Explicit consent before hosted LLM processing.
