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
