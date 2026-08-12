# Local Storage

FoxPilot uses SQLite as its primary local store.

## Location

The database is created at:

```text
~/.foxpilot/foxpilot.sqlite3
```

The database uses WAL mode and stores jobs, relevance classifications, match results, provider/model metadata, and application state. Resume files and profiles remain in the same local data directory and are never committed.

## Portability

`~/.foxpilot/` expands to the current operating-system user's home directory. It is intentionally machine-local and is created automatically when the user runs `foxpilot init` or when the storage layer first opens the database.

The repository contains code, safe configuration examples, and source-search configuration. It does not contain a user's resume, browser session, SQLite database, profile, job history, or match history. Those are created independently on each machine.

On a new machine:

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
foxpilot init --resume /absolute/path/to/resume.pdf
foxpilot migrate
```

The migration command also copies an existing legacy `~/.career-agent` database and profile into `~/.foxpilot` before importing legacy repository job files. The resume path in `config.json` is machine-specific. Never copy that config file between machines without updating the path. A cloned repository is clean and runnable, but each user must configure their own resume, preferences, Ollama model, and source authentication.

Local state is persistent, not temporary. It remains until the user backs it up or deletes `~/.foxpilot/`. Existing `~/.career-agent/` data is supported as a legacy fallback. The future hosted mode will replace this directory with an authenticated per-user storage volume.

## Scan Lock

FoxPilot writes an advisory lock at `~/.foxpilot/scan.lock` while ingestion, filtering, profile extraction, and matching run. A second local scan exits safely instead of competing for browser state, SQLite writes, or LLM capacity. The lock is released when the process exits normally.

## Existing JSON Data

Older prototype job files under `data/jobs/` can be imported once:

```bash
foxpilot migrate
```

Normal scans also perform an idempotent legacy import before ingestion. New writes go to SQLite; JSON files are not the primary store.

## Backup

Stop active scans before copying the database:

```bash
cp ~/.foxpilot/foxpilot.sqlite3 ~/.foxpilot/foxpilot.backup.sqlite3
```

For a consistent backup while the app is active, use SQLite's backup tooling rather than copying only one WAL component. Docker deployment will use a named persistent volume and documented backup commands.

## Docker

No Docker installation is required for the current CLI workflow. Docker becomes necessary when the FastAPI and React services are introduced for local web deployment. The database will be mounted as persistent storage rather than kept inside an ephemeral container layer.
