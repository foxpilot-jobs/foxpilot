# Architecture Decisions

## Local-first AI

Ollama is the default provider because it supports a no-API-key local workflow. Profile extraction and matching use a shared provider interface. OpenAI remains an optional adapter for users who choose hosted-model quality and accept cost and data-sharing tradeoffs.

## SQLite before hosted storage

SQLite provides durable querying, history, migrations, backup, and zero hosting cost. A hosted database is deferred until there is a validated multi-user product need.

## Adapter-based sources

Job sources differ in APIs, HTML, authentication, rate limits, and terms. Each source must be isolated behind a common interface rather than embedded in the pipeline.

## CLI before dashboard

The CLI validates the core value proposition and keeps the first release small. A dashboard is an optional presentation layer over the same services and storage, not a second business-logic implementation.

## No autonomous applications

Applications and outreach have external consequences and require user judgment. The product may prepare context or open the source URL, but explicit confirmation is required before any outbound action.

## Same-repository web monorepo

The React web/PWA lives in `apps/web` in the same repository as the Python core and API. This keeps product contracts, security rules, and release changes reviewable together while allowing independent frontend builds.

## Database portability

SQLAlchemy is the repository boundary. SQLite remains the default local database, while PostgreSQL is selected with `DATABASE_URL` for hosted mode. Alembic owns schema changes so hosted deployments do not rely on implicit table creation.

## Responsive PWA before native mobile

The first browser product targets desktop and mobile layouts through one responsive React application and PWA capabilities. Native mobile apps are deferred until usage demonstrates a need for platform-specific capabilities.

## Source Adapter Expansion

Job ingestion uses isolated adapters with a shared normalized job contract. Public HTTP sources use their documented public endpoints; authenticated browser access runs locally and is not shared with hosted services unless redistribution rights exist. Adapters are independently rate-limited and failure-isolated so one source outage cannot prevent other sources from contributing jobs. Source-specific configuration is explicit, particularly for ATS board slugs.

## Shared Canonical Job Corpus

Public and licensed ingestion builds a shared canonical job corpus. A canonical job may have multiple source listings, which are retained for attribution and fallback links. Cross-source merging is conservative and does not merge same-title roles without strong description evidence. User profiles, match results, applications, and notes remain user-scoped. Listing availability is checked separately and inactive listings are retained but hidden by default. Authenticated local imports are private listings unless explicitly marked public by an authorized ingestion process.

## India Production Architecture

Limited beta staging uses Railway Hobby in Singapore for speed and low operational overhead, with an explicit small-user/no-SLA boundary. Production targets AWS `ap-south-1` (Mumbai) with managed PostgreSQL, encrypted object storage, a durable queue, separate API and worker services, and authenticated API-only access for web and CLI clients. Local SQLite/Ollama remains supported for privacy and development, but production clients must not connect directly to PostgreSQL. See `SYSTEM_DESIGN.md` for the complete boundary and rollout contract.
