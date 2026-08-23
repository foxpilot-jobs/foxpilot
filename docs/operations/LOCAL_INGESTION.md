# Local Ingestion Runbook

This runbook operates the shared job corpus. Public/API ingestion can run from a trusted local machine or scheduler. Authenticated browser ingestion must remain local and must not upload browser cookies or passwords to Railway.

## Architecture

```text
Public APIs / local permitted browser sessions
        |
        v
foxpilot ingest -> shared PostgreSQL jobs + job_listings
        |
        +-> foxpilot check-availability -> active/inactive listings
        |
        +-> Railway worker -> profile generation and user-specific matching
```

Public jobs are shared. Authenticated or private imports must be marked private and restricted to their owner unless the source terms and account permit redistribution.

## One-Time Setup

1. Install the repository environment:

   ```bash
   ./scripts/bootstrap.sh
   source .venv/bin/activate
   ```

2. Configure a `.env` file outside version control:

   ```env
   DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
   FOXPILOT_SOURCES_CONFIG=/absolute/path/to/data/sources.json
   ```

3. Confirm the database is reachable and apply migrations:

   ```bash
   alembic upgrade head
   ```

4. Configure public sources in `data/sources.json`. Public aggregators are enabled by default. ATS sources require company board slugs:

   ```json
   {
     "greenhouse": {"boards": [{"slug": "example", "company": "Example Co"}]},
     "ashby": {"boards": [{"slug": "example", "company": "Example Co"}]},
     "lever": {"boards": [{"slug": "example", "company": "Example Co"}]}
   }
   ```

## Scheduled Public Ingestion

Run this command from the repository root:

```bash
source .venv/bin/activate
foxpilot ingest
```

Example cron schedule, every six hours:

```cron
0 */6 * * * cd /absolute/path/to/career-agent && .venv/bin/foxpilot ingest >> /absolute/path/to/logs/foxpilot-ingest.log 2>&1
```

The command is idempotent. Existing source listings are refreshed, new listings are added, and canonical jobs may collect multiple source links.

## Scheduled Availability Checks

Run once daily to check stale public listing URLs:

```bash
source .venv/bin/activate
foxpilot check-availability --limit 500 --stale-after-hours 24
```

Example cron schedule:

```cron
30 2 * * * cd /absolute/path/to/career-agent && .venv/bin/foxpilot check-availability --limit 500 --stale-after-hours 24 >> /absolute/path/to/logs/foxpilot-availability.log 2>&1
```

Transient errors such as `403`, `429`, and `5xx` remain unknown. Confirmed `404` and `410` responses mark a listing inactive. History is retained.

## Authenticated Local Sources

Use the local Playwright workflow only for sources where access and automation are permitted. Keep the browser profile and credentials on the local machine. Do not set a local browser session as a Railway secret. Private imported listings must not be published into the shared corpus.

After ingestion, the Railway API can match shared active jobs against each authenticated user's profile. Matching results, application status, and notes remain user-specific.

## Railway Worker

The API only queues profile-generation, scan, and matching jobs when `FOXPILOT_WORKER_MODE=external`. Run a separate Railway service with:

```bash
python -m career_agent.worker
```

The worker must use the same `DATABASE_URL`, LLM settings, and migrations as the API service. It does not need a public domain.

## Verification

After ingestion:

1. Check the command output for per-source counts and failures.
2. Open the dashboard with no profile and confirm active jobs appear.
3. Open a job card and confirm all available source links are shown together.
4. Upload a profile and run matching; confirm only that user receives match evidence.
5. Run availability checks and confirm closed links disappear from the default view.
6. Use `include_inactive=true` only when auditing closed-job history.

Never place database credentials, browser state, resume content, or provider keys in this runbook, cron arguments, source configuration, or logs.
