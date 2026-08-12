# Production Baseline

## Product Contract

Career Agent is a local-first job discovery and decision-support product. Its job is to help users find fewer, better opportunities and make faster, more informed application decisions. It is not an autonomous applicant or a guarantee of interview outcomes.

## Approved Stack

- Python 3.11 or newer
- `pyproject.toml` as the dependency and build source of truth
- Typer for the CLI
- Pydantic for validated domain models
- SQLite for durable local state
- Ollama as the default local LLM provider
- Optional OpenAI provider behind a provider interface
- `httpx` plus BeautifulSoup for HTTP-based sources
- Playwright only for sources that require browser rendering
- pytest, Ruff, and mypy or pyright

## Data Rules

- All user data belongs outside the repository by default.
- Use a configurable data directory, with `~/.career-agent/` as the intended default.
- Resume files, extracted text, profiles, job descriptions, browser sessions, match results, and application history are local data.
- Test fixtures must be synthetic or sanitized. The maintainer's current resume is temporary local integration input only.
- Remote LLM use must be opt-in and clearly disclosed.

## Engineering Rules

- Define interfaces at integration boundaries: LLM providers, job sources, storage, notifications.
- Validate all external input before persistence or model use.
- Use deterministic identifiers and idempotent writes.
- Use retries only for transient failures, with bounded backoff and rate limits.
- One source failure must not prevent other sources from running.
- Never silently discard data or silently change user configuration.
- Use structured logging rather than scattered prints in new code.
- Keep compatibility code only when required by persisted data or a documented migration.

## Quality Gates

Every phase must leave the project in a runnable state and include:

- Unit tests for new business logic.
- Fixture-based tests for external integrations.
- Formatting and linting passing.
- Type checking for changed modules.
- Documentation for user-visible or architectural changes.
- Explicit handling of secrets and private data.

## Product Safety

- Match scores must include evidence and limitations.
- The user must confirm any application or outbound communication.
- Do not bypass authentication, CAPTCHAs, robots controls, rate limits, or access restrictions.
- Do not present third-party job data as owned or guaranteed by the project.
- Do not make hiring, discrimination, or eligibility claims from protected attributes.

## Web And API Rules

- The repository is a monorepo: `apps/web` for React, `services/api` for FastAPI, and `src/career_agent` for domain/application services.
- Browser code talks only to the versioned API and never directly to Ollama, job sources, or SQLite.
- Keep API schemas explicit and test them. Do not expose internal models or stack traces as public responses.
- Treat the web app as a responsive PWA before considering native mobile clients.
- Hosted mode must enforce authentication, user data isolation, retention controls, and explicit remote-provider consent.

## Toolchain And Registry Rules

- Use `python3` and the repository virtual environment for Python work.
- Use the repository bootstrap commands so Python dependencies resolve from public PyPI.
- Use `npm` for JavaScript work; `.npmrc` pins the project to the public npm registry.
- Do not depend on machine-specific package-manager configuration for installation or deployment.
