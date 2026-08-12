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

## Phase 2: Local Intelligence

- Add provider interfaces and Ollama implementation.
- Add optional OpenAI implementation.
- Generalize resume/profile ingestion.
- Validate structured model output and record model metadata.

## Phase 3: Source Platform

- Define the canonical job model and source interface.
- Stabilize Greenhouse, then add Lever, RemoteOK, Remotive, and HN.
- Add deduplication, retries, rate limits, fixtures, and source health.
- Treat Indeed and LinkedIn as optional integrations with explicit limitations.

## Phase 4: Durable Workflow

- Migrate from JSON outputs to SQLite.
- Add saved jobs, application statuses, notes, history, export, and deletion.

## Phase 5: User Experience

- Ship setup, scan, matches, job, application, and export commands.
- Add HTML reports and a later optional Streamlit dashboard.

## Phase 6: Automation And Release

- Add opt-in local scheduling and notifications.
- Add release automation, sanitized fixtures, documentation publishing, and brand validation.
