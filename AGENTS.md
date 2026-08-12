# Agent Instructions

Before changing code, read `.agents/BASELINE.md` and the relevant documents under `docs/`.

These rules apply to every agent working in this repository:

- Treat user resumes, browser profiles, job records, match results, and credentials as private data.
- Never commit secrets, personal data, browser state, generated results, or unreviewed third-party content.
- Use the approved architecture; do not add a second framework or provider without documenting the decision.
- Prefer the smallest production-safe change and preserve clear module boundaries.
- Add or update tests for behavior changes.
- Run formatting, linting, type checking, and relevant tests before declaring work complete.
- Update documentation when behavior, configuration, architecture, or user workflow changes.
- Keep external job-source integrations isolated, rate-limited, observable, and compliant with their terms.
- Never submit applications, recruiter messages, or external actions without explicit user confirmation.
- Do not commit changes. The repository owner handles commits and publishing.
