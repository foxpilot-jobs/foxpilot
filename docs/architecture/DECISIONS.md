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

## Frontend testing (deferred, framework chosen)

`apps/web` previously had no automated test framework. CI now runs Prettier, ESLint, Stylelint, Vitest, and a type-checked production build (`npm run check`).

The chosen stack for when frontend tests are added is **Vitest + React Testing Library**, with `@testing-library/jest-dom` and `@testing-library/user-event`, running in a `jsdom` environment. Rationale: Vitest reuses the existing Vite config and transform pipeline directly (no parallel Babel/webpack setup to maintain), it is the de facto standard pairing for Vite + React + TypeScript projects, and React Testing Library's user-facing query model matches how this app's components are already structured (accessible roles/labels rather than implementation-detail selectors).

The initial coverage prioritizes the changed behaviors: `ThemeProvider` persistence, the `AppShell` sidebar collapse/mobile-drawer toggle, and the `Modal` confirmation flow. Future behavior changes should extend this suite.

## Workspaces as the multi-profile primitive

A workspace is a named, user-owned job-search context. Each workspace carries its own resume, extracted profile, target-role intent, match results, and application history. This is intentionally broader than "multiple resumes": the same resume may produce a different profile when the user targets a different role family (e.g. "Senior IC" vs "Engineering Manager"). A user may hold any number of workspaces; exactly one is active at a time. Switching activates a different workspace atomically.

Implementation is a `workspaces` table (`workspace_id`, `user_id`, `name`, `is_active`, `created_at`, `updated_at`). The `profiles` table gains a `workspace_id` foreign key and a unique constraint on `(user_id, workspace_id)`. Background jobs and match results reference `workspace_id` for full isolation. Deleting a workspace hard-deletes the profile row (resume text + extracted profile) to satisfy SYSTEM_DESIGN's retention requirement. Match results and applications referencing the workspace are also deleted. No soft-delete is used for workspaces because there is no operational need to recover a deleted workspace; the user must re-upload the resume if they want to recreate it.

Original resume bytes in encrypted object storage is a deferred architecture item (see SYSTEM_DESIGN implementation order step 6). For now, resume text is stored in Postgres and is scrubbed on workspace or profile deletion. The API must delete the profile row immediately and synchronously on a DELETE request; no background job is needed.

## India Production Architecture

Limited beta staging uses Railway Hobby in Singapore for speed and low operational overhead, with an explicit small-user/no-SLA boundary. Production targets AWS `ap-south-1` (Mumbai) with managed PostgreSQL, encrypted object storage, a durable queue, separate API and worker services, and authenticated API-only access for web and CLI clients. Local SQLite/Ollama remains supported for privacy and development, but production clients must not connect directly to PostgreSQL. See `SYSTEM_DESIGN.md` for the complete boundary and rollout contract.
