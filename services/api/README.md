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

Set `FOXPILOT_ENV=production` and a long random `FOXPILOT_API_TOKEN` before exposing the API outside localhost. The current token guard protects the deployment boundary; multi-user OIDC/OAuth is still required for public launch.
