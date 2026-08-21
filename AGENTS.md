# Agent Instructions

Before changing code, read `.agents/BASELINE.md` and the relevant documents under `docs/`.

These rules apply to every agent working in this repository:

- Treat user resumes, browser profiles, job records, match results, and credentials as private data.
- Never commit secrets, personal data, browser state, generated results, or unreviewed third-party content.
- Use the approved architecture; do not add a second framework or provider without documenting the decision.
- Read `docs/architecture/SYSTEM_DESIGN.md` before architectural changes; it is the source of truth for production boundaries and implementation constraints.
- Prefer the smallest production-safe change and preserve clear module boundaries.
- Add or update tests for behavior changes.
- Run formatting, linting, type checking, and relevant tests before declaring work complete.
- Update documentation when behavior, configuration, architecture, or user workflow changes.
- Keep external job-source integrations isolated, rate-limited, observable, and compliant with their terms.
- Never submit applications, recruiter messages, or external actions without explicit user confirmation.
- Do not commit changes. The repository owner handles commits and publishing.
- Use the repository bootstrap commands for dependencies. They explicitly select public package registries and must not depend on machine-level package-manager configuration.
- Keep frontend work under `apps/web` and API adapter work under `services/api`; do not put browser logic in Python scrapers or provider modules.
- The API and CLI must share Python application services. Do not duplicate matching, profile, storage, or source logic in the frontend.
- Frontend changes must preserve responsive desktop/mobile behavior, accessibility, typed API contracts, and the local-first privacy model.
