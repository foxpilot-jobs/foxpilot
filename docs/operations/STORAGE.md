# Local Storage

Career Agent uses SQLite as its primary local store.

## Location

The database is created at:

```text
~/.career-agent/career_agent.sqlite3
```

The database uses WAL mode and stores jobs, relevance classifications, match results, provider/model metadata, and application state. Resume files and profiles remain in the same local data directory and are never committed.

## Portability

`~/.career-agent/` expands to the current operating-system user's home directory. It is intentionally machine-local and is created automatically when the user runs `career-agent init` or when the storage layer first opens the database.

The repository contains code, safe configuration examples, and source-search configuration. It does not contain a user's resume, browser session, SQLite database, profile, job history, or match history. Those are created independently on each machine.

On a new machine:

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
career-agent init --resume /absolute/path/to/resume.pdf
career-agent migrate
```

The resume path in `config.json` is machine-specific. Never copy that config file between machines without updating the path. A cloned repository is clean and runnable, but each user must configure their own resume, preferences, Ollama model, and source authentication.

Local state is persistent, not temporary. It remains until the user backs it up or deletes `~/.career-agent/`. The future hosted mode will replace this directory with an authenticated per-user storage volume; Docker will mount it as a persistent volume rather than storing it in an ephemeral container.

## Existing JSON Data

Older prototype job files under `data/jobs/` can be imported once:

```bash
career-agent migrate
```

Normal scans also perform an idempotent legacy import before ingestion. New writes go to SQLite; JSON files are not the primary store.

## Backup

Stop active scans before copying the database:

```bash
cp ~/.career-agent/career_agent.sqlite3 ~/.career-agent/career_agent.backup.sqlite3
```

For a consistent backup while the app is active, use SQLite's backup tooling rather than copying only one WAL component. Docker deployment will use a named persistent volume and documented backup commands.

## Docker

No Docker installation is required for the current CLI workflow. Docker becomes necessary when the FastAPI and React services are introduced for local web deployment. The database will be mounted as persistent storage rather than kept inside an ephemeral container layer.
