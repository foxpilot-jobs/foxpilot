# Deployment

## Baseline

The supported baseline is local execution:

```text
React web/PWA -> FastAPI -> Python services -> SQLite + Ollama
```

This preserves privacy and avoids mandatory hosting costs.

## Local Docker Deployment

Docker Compose will package the API and web app while Ollama remains a local model service. Persistent volumes must store SQLite data, Ollama models, and user data outside container layers. The compose stack must not contain credentials.

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

## Production Requirements

- Versioned API endpoints.
- Authentication and per-user data isolation.
- TLS at the edge.
- Secret injection through deployment configuration.
- Health and readiness checks.
- Structured logs without resume contents or credentials.
- Database backups and restore verification.
- Rate limits for source adapters and user-triggered scans.
- Explicit consent before hosted LLM processing.
