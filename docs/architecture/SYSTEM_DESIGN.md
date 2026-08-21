# FoxPilot System Design

Status: target production architecture

This document is the source of truth for system boundaries, deployment shape, data ownership, and implementation constraints. Before changing architecture or adding a cross-cutting feature, update this document or add an entry to `DECISIONS.md` first.

## Product Contract

FoxPilot is a job discovery and career decision-support system. It finds fewer, better opportunities and explains why a role may fit. It does not apply to jobs, contact recruiters, or make hiring/eligibility decisions without explicit user confirmation.

The primary quality objective is qualified opportunities reviewed per hour of user effort. Relevance and evidence take priority over maximum listing volume.

## Target Production Shape

```text
Browser / PWA
    |
    | HTTPS, authenticated API
    v
FastAPI API service  --->  OpenAI provider (explicit user consent)
    |
    | enqueue durable jobs
    v
Managed queue  --->  Python worker service
                         |
                         +--> source adapters
                         +--> deterministic relevance/ranking
                         +--> bounded AI enrichment
                         +--> PostgreSQL
                         +--> encrypted object storage

Static web assets ---> CDN/object storage
```

The first limited staging region is Railway Singapore for low operational overhead and a small beta audience. The production target remains AWS `ap-south-1` (Mumbai) because it provides the broadest production primitives in an India region: managed PostgreSQL, object storage, queues, secrets, compute, TLS, logging, and CDN integration.

## Approved Languages And Responsibilities

- Python 3.11+: domain logic, source adapters, profile processing, relevance ranking, workers, API services, migrations, and CLI.
- React + TypeScript: responsive web/PWA presentation and typed API client only.
- SQL: migrations, indexes, and carefully reviewed repository queries.
- YAML: local Compose and CI configuration.
- Terraform or equivalent infrastructure-as-code: required before repeatable production infrastructure is created.

Do not rewrite the Python core or React client into another language without a measured requirement and an architecture decision. Keep browser automation in source adapters and keep business logic out of React.

## Environments

### Local CLI

```text
CLI -> SQLite -> native Ollama or explicit OpenAI
CLI -> host Playwright -> job sources
```

This mode is private and requires no Docker. It is the development and offline-friendly baseline.

### Local Web

```text
Web -> FastAPI -> PostgreSQL
Host scanner -> PostgreSQL
FastAPI -> host Ollama or OpenAI
```

This is a development mode only. Local CLI and web data are not implicitly merged across databases or users.

### Production

```text
Web/CLI -> authenticated API -> managed PostgreSQL
                         -> durable worker queue
                         -> encrypted object storage
```

Production clients must not receive PostgreSQL credentials. The API and workers are the only database writers.

## Data Ownership

### Shared job data

- Canonical job identifier.
- Source and source identifier.
- Title, company, location, URL, description, timestamps.
- Content hash and source metadata.

Shared job records are deduplicated and may be reused across users.

### User-scoped data

- Authentication identities and sessions.
- Original resume object reference.
- Extracted resume text.
- Career profile and profile revision.
- Preferences and search constraints.
- User-specific relevance evidence and match results.
- Applications, notes, and decisions.

Every user-scoped query must enforce ownership in the repository layer and API authorization layer. Production PostgreSQL should add row-level security or equivalent defense-in-depth after the migration path is validated.

Original resumes belong in private encrypted object storage. Extracted text and structured profiles may be stored in PostgreSQL only with explicit retention policy and user deletion support.

## Request And Job Boundaries

HTTP requests must remain short. Profile extraction, source scans, description fetching, and matching are background jobs.

Each job must have:

- User ID.
- Input/profile revision or content hash.
- Status and timestamps.
- Attempt count.
- Bounded retry policy.
- Error classification.
- Idempotency key.
- Progress metadata where useful.

Workers must claim jobs atomically and use leases/heartbeats. The repository now includes a durable database-backed worker for low-traffic staging and production-shaped local testing; set `FOXPILOT_WORKER_MODE=external` and run `python -m career_agent.worker`. AWS production should replace the database polling transport with SQS when traffic or operational requirements justify it. FastAPI in-process background tasks are acceptable only for local development, not production.

## AI Boundary

Python must handle all deterministic work first:

- Resume text extraction.
- Resume and job hashing.
- Search query generation from the profile.
- Source filtering and normalization.
- Deduplication.
- Location/work-type/seniority constraints.
- Skill and title evidence extraction.
- Candidate pre-ranking.
- Cache decisions.

AI is reserved for semantic work:

- Ambiguous profile role normalization.
- High-value or ambiguous job comparison.
- Explanation, gap analysis, and evidence summarization.

The intended matching flow is:

```text
all discovered jobs
    -> Python candidate score
    -> reject obvious low-fit jobs
    -> cache obvious deterministic decisions
    -> AI only for top/ambiguous candidates
```

Provider use must be bounded, observable, schema-validated, and consent-aware. OpenAI is opt-in because resume and job data leave the local environment. Ollama is the local provider and must not be required for the OpenAI deployment.

## Source Boundary

Each source is an isolated adapter with:

- Documented access method and terms.
- Profile-derived query input.
- Source-specific rate limit.
- Timeout and bounded retries.
- Normalized job output.
- Failure isolation.
- Health and ingestion metrics.

Do not add generic global scraping logic that bypasses source restrictions. Authenticated browser sources remain separate from public HTTP sources.

## API And CLI Contract

The API is the production source of truth. The CLI may perform local browser ingestion, but production CLI operations must submit results through authenticated API endpoints rather than connecting directly to PostgreSQL.

Required production CLI capabilities:

- Device/login authentication.
- Profile upload and profile revision status.
- Authenticated scan submission.
- Authenticated match submission.
- Paginated job/match retrieval.
- Resume-safe retry and job status polling.

The frontend and CLI must use versioned API contracts. Neither may implement matching or profile business rules independently.

## Security Requirements

- TLS at the edge and encrypted database/storage services.
- Secrets injected by the deployment platform, never committed.
- HTTP-only, secure, same-site session cookies.
- CSRF/origin protection for browser mutations.
- Per-user authorization on every user-scoped read/write.
- API and source rate limits backed by shared infrastructure.
- Resume deletion and retention controls.
- Structured logs without resume text, API keys, or full job descriptions.
- Audit events for authentication, profile changes, scans, matches, and applications.
- Explicit consent and disclosure for OpenAI processing.

## Production AWS Shape

The recommended initial AWS implementation in Mumbai is:

- CloudFront plus S3 for the React static frontend.
- ECS Fargate or App Runner for the FastAPI API.
- A separate worker service for scans/profile/matching.
- RDS PostgreSQL for durable application data.
- S3 with SSE-KMS for original resumes and exports.
- SQS for durable background jobs.
- Secrets Manager for database, OpenAI, SMTP, and OAuth credentials.
- CloudWatch for logs, metrics, alarms, and worker health.
- ACM and Route 53 for TLS and domain routing.

For a low-cost single-server proof of deployment, a Mumbai VM running Docker Compose can be used temporarily. It is not equivalent to the managed production topology and does not provide managed backups, failover, or durable worker guarantees by itself. Railway Hobby in Singapore is the preferred limited-beta staging option; it is not India-region hosting or a production availability commitment.

## Cost And Free-Tier Position

There is no dependable permanent free tier that simultaneously provides India-region compute, managed PostgreSQL, encrypted object storage, durable workers, backups, and production availability.

- Free frontend hosting is practical through a global CDN/static host.
- Free backend tiers are suitable for demos but may sleep or have low CPU/RAM.
- Free PostgreSQL offerings may be time-limited, region-limited, or unsuitable for production backups.
- AWS offers new-account credits/free-tier benefits, but production AWS usage is pay-as-you-go and requires billing alerts.

The recommended path is to keep the frontend inexpensive/free where possible and pay for the minimum managed backend/database footprint in Mumbai once real users or persistent data justify it.

For the current prototype, an AWS Free Tier/credits staging profile may use a single small Mumbai compute service for API and worker, a free-tier-eligible PostgreSQL option when the account qualifies, and free/low-volume S3, SQS, CloudWatch, and CDN usage. This profile is explicitly staging-only: it has limited capacity, no guaranteed high availability, and requires billing alerts. It must not be presented as production-grade or used for sensitive multi-user traffic without the managed production controls above.

## Implementation Order

1. Add production environment validation and secret injection.
2. Add authenticated API-only CLI operations.
3. Replace in-process background tasks with a durable queue and worker.
4. Add profile revisions, idempotency, atomic job claiming, and retry classification.
5. Add managed PostgreSQL migrations, indexes, backups, and restore checks.
6. Add encrypted resume object storage and deletion/retention controls.
7. Add Python pre-ranking to reduce AI calls and improve latency.
8. Add production deployment manifests/IaC for AWS Mumbai.
9. Configure the domain, TLS, OAuth redirect URIs, SMTP, monitoring, and billing alerts.

## Decision Rule For Future Changes

Prefer the smallest change that preserves these boundaries. If a proposed implementation introduces direct client-to-database access, a new business-logic copy in the frontend, an unbounded AI call, an in-process production job, a new language/framework, or unscoped user data, stop and update this design plus `DECISIONS.md` before implementing it.
