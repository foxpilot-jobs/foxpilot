# Security And Privacy

## Local Data

Resumes, extracted text, career profiles, job records, match results, application history, and browser sessions are sensitive local data. They belong in the user's data directory and are excluded from git.

## LLM Providers

Ollama is the default local path. Hosted providers are optional. The CLI must identify the active provider and warn when resume or job data will leave the machine.

## Browser Sessions

Persistent browser profiles contain cookies, login state, history, and possibly credentials. They must never be committed, shared, or used as a default repository fixture. Users should use a dedicated profile and revoke sessions if one is exposed.

## External Sources

Adapters must respect published terms, robots rules where applicable, authentication boundaries, rate limits, and service stability. The project will not bypass controls or guarantee access to a source.

## Repository Hygiene

Run a secret and personal-data scan before publishing. If sensitive files were committed previously, remove them from history using the repository owner's approved history-rewrite process before making the repository public.

## User Controls

The product must provide export and deletion paths. No outbound application, email, or message may occur without explicit confirmation.

## Hosted Identity And Isolation

Hosted deployments must not rely on local mode or the shared token guard. FoxPilot's production path is native branded authentication backed by PostgreSQL users, secure password hashing, HTTP-only sessions, email verification, and password recovery.

Jobs are a shared catalog. Matches and application history are keyed by `user_id` and `job_id`, so career decisions and private notes are isolated between identities. Existing local records are migrated to `local-user` by migration `0002_user_owned_state`.
