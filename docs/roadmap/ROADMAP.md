# Roadmap

Every phase ends with tests, documentation, and a runnable state. Work is not considered complete when only the happy path works.

## Phase 0: Secure And Document

- Remove browser sessions and personal generated data from the repository.
- Add gitignore rules, MIT license, README, agent baseline, and operating docs.
- Document product boundaries, privacy, source compliance, and decisions.

## Phase 1: Production Foundation

- Move to a typed `career_agent` package.
- Add `pyproject.toml`, Typer CLI, configuration, logging, and error types.
- Cover current filtering and normalization behavior with tests.
- Add CI quality gates.

## Phase 2: Local Intelligence (Foundation Complete)

- Provider interfaces and Ollama implementation.
- Optional OpenAI implementation.
- Shared configuration and generic resume/profile ingestion.
- Validated structured model output.
- Follow-up: provider metadata, model evaluation fixtures, and quality benchmarks.

## Phase 3: Source Platform

- Define the canonical job model and source interface. **In progress.**
- Stabilize Greenhouse, then add Lever, RemoteOK, Remotive, and HN. **In progress.**
- Add deduplication, retries, rate limits, fixtures, and source health. **In progress.**
- Treat Indeed and LinkedIn as optional integrations with explicit limitations.

### Source Expansion Notes

- Greenhouse `my.greenhouse.io` remains an authenticated browser source because its search experience requires a saved user session. Authentication, CAPTCHA, robots, and rate limits are never bypassed.
- Lever is configured by public board slug because Lever does not provide a universal public global-search endpoint. Empty configuration means the adapter is skipped without failing the scan.
- RemoteOK and Remotive are public APIs queried with bounded timeouts, a descriptive user agent, and conservative request pacing.
- Hacker News uses the public Algolia search API for `Ask HN: Who is hiring?` posts. The adapter treats post text as untrusted job content and never submits or contacts anyone.
- Every source writes the same canonical job shape with a source-specific ID. Database upserts provide idempotency; source failures are reported and do not prevent other sources from running.

## Phase 4: Durable Workflow (Storage Portability Complete)

- Migrate from JSON outputs to SQLite.
- Import legacy job files idempotently.
- Persist relevance, provider/model metadata, and match results.
- Support PostgreSQL through `DATABASE_URL` and Alembic migrations.
- Add saved jobs, application statuses, notes, history, export, and deletion.

## Phase 5: API And Web Foundation

- Extract reusable application services from compatibility scripts.
- Add a FastAPI HTTP adapter with versioned endpoints and OpenAPI documentation.
- Add the React + TypeScript responsive web/PWA under `apps/web`.
- Keep the web app dependent on the API, never on scrapers or LLM providers directly.
- Add contract tests between API responses and frontend query types.

## Phase 6: Local And Hosted Deployment

- Add Docker Compose for API, web, SQLite, and Ollama local deployment.
- Add PostgreSQL configuration without coupling domain services to one database.
- Add background scan scheduling and job execution controls.
- Add health checks, structured logs, backups, and secret configuration.

## Phase 7: User Experience And Release

- Ship setup, scan, matches, job, application, and export commands.
- Ship the responsive web/PWA workflow.
- Add opt-in local scheduling and notifications.
- Add release automation, sanitized fixtures, documentation publishing, and brand validation.
