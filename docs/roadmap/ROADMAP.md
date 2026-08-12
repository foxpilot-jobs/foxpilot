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

- Define the canonical job model and source interface.
- Stabilize Greenhouse, then add Lever, RemoteOK, Remotive, and HN.
- Add deduplication, retries, rate limits, fixtures, and source health.
- Treat Indeed and LinkedIn as optional integrations with explicit limitations.

## Phase 4: Durable Workflow

- Migrate from JSON outputs to SQLite.
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
