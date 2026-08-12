# Career Agent API

The API will be a FastAPI HTTP adapter over reusable application services in `src/career_agent`.

Responsibilities:

- Authentication and user isolation in hosted mode.
- Request validation and response serialization.
- Versioned endpoints and OpenAPI documentation.
- Health and readiness checks.
- No direct scraping, LLM prompting, or database-specific business logic.

The API implementation starts after the SQLite repository and application-service boundaries are stable.
