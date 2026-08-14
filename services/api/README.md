# FoxPilot API

The API will be a FastAPI HTTP adapter over reusable application services in `src/career_agent`.

Responsibilities:

- Authentication and user isolation in hosted mode.
- Request validation and response serialization.
- Versioned endpoints and OpenAPI documentation.
- Health and readiness checks.
- No direct scraping, LLM prompting, or database-specific business logic.

The initial API implementation is available at `services/api/app.py`. Run it locally with:

```bash
source .venv/bin/activate
uvicorn services.api.app:app --reload --port 8000
```

The API is currently intended for local use. Authentication and hosted per-user isolation are required before public deployment.

For local Compose mode, the API runs in Docker and reads PostgreSQL. The host scan must set `DATABASE_URL` to the published PostgreSQL port before writing jobs for the web app to display.

For hosted database configuration, set `DATABASE_URL` to a PostgreSQL `postgresql+psycopg://...` URL and run `alembic upgrade head` before starting the service.

## Authentication modes

Local mode is the default and uses the explicit `local-user` identity. It is intended only for a private local deployment:

```env
FOXPILOT_ENV=local
FOXPILOT_AUTH_MODE=local
```

Token mode is suitable for staging and non-browser automation. The token maps to one stable identity, not multiple users:

```env
FOXPILOT_AUTH_MODE=token
FOXPILOT_API_TOKEN=<long-random-secret>
FOXPILOT_TOKEN_USER_ID=staging-user
```

Hosted production will use native FoxPilot authentication with branded registration, secure password hashing, HTTP-only sessions, email verification, and password recovery. Until that native auth layer lands, token mode is a temporary single-user staging guard and is not suitable for a public multi-user deployment.

The current `/api/v1/me` endpoint confirms the identity FoxPilot extracted. Local mode returns `local-user`; token mode returns `FOXPILOT_TOKEN_USER_ID`.
