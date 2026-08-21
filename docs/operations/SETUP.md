# FoxPilot Setup

This is the authoritative setup guide for a fresh machine. The simplest supported deployment is a local CLI using SQLite and either OpenAI or native Ollama. Docker is not required for this mode.

## Prerequisites

- Python 3.11 or newer.
- Git.
- An OpenAI API key when using the OpenAI provider.
- A local PDF resume.
- Chromium dependencies for Playwright. The bootstrap script installs the browser binary.

Check Python:

```bash
python3 --version
```

## Install

Clone the repository and create the project environment:

```bash
git clone <repository-url> career-agent
cd career-agent
./scripts/bootstrap.sh
source .venv/bin/activate
```

The bootstrap script creates `.venv`, installs Python dependencies from public PyPI, installs the editable FoxPilot package, and installs Playwright Chromium. It does not install Docker, Ollama, or Node.

## Configure OpenAI

Copy the environment example and edit `.env`:

```bash
cp .env.example .env
```

Set these values:

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=replace-with-your-key
DATABASE_URL=
```

Use a model available to your OpenAI account. Keep `.env` private. Never put the API key in `config.json`, source code, shell history, or git.

OpenAI receives resume text and job descriptions. This is different from the default local Ollama mode and may incur API charges. Use a provider/model approved for the sensitivity of your data.

## Initialize The Local Profile

Point FoxPilot to the resume:

```bash
foxpilot init --resume "/absolute/path/to/resume.pdf" --provider openai --model gpt-4o-mini
```

If the configuration already exists, the command updates it. The profile is stored outside the repository under:

```text
~/.foxpilot/career_profile.json
```

Generate the profile:

```bash
python src/create_profile.py
```

Profile extraction is cached by resume path and content. Repeating the command with the same resume skips the OpenAI call. Changing the path or file contents regenerates the profile.

## Run A Scan

Validate the local installation without fetching jobs:

```bash
foxpilot scan --dry-run
```

Run the profile-driven scan:

```bash
foxpilot scan
```

The scan uses the saved profile to derive search roles, launches the persistent Greenhouse browser when needed, fetches public sources, filters candidates, and matches eligible jobs. The first Greenhouse scan may require manual sign-in. The browser session is stored in local FoxPilot data and must not be committed.

SQLite state and job history are stored under:

```text
~/.foxpilot/
```

## Repeated Runs

```bash
source .venv/bin/activate
python src/create_profile.py  # skips OpenAI when the resume is unchanged
foxpilot scan                 # reuses cached profile and cached matches
```

Unchanged jobs reuse their existing match result. New or changed job descriptions are analyzed again.

## Optional Local API/Web

The CLI is the recommended no-Docker workflow. The FastAPI service can also run against local SQLite:

```bash
source .venv/bin/activate
uvicorn services.api.app:app --reload --port 8000
```

The React web client has separate Node 22+ requirements and is documented in `README.md` and `RUN_MODES.md`. The web app does not directly access SQLite or OpenAI; it talks to the API.

## Troubleshooting

`python: command not found`: activate `.venv`, or use `.venv/bin/python`.

`foxpilot: command not found`: activate `.venv`, or use `.venv/bin/foxpilot`.

`OPENAI_API_KEY is required`: confirm `.env` contains `OPENAI_API_KEY` and that the command is run from the repository or another directory where dotenv can find the file.

`Resume not found`: use an absolute path and verify it exists:

```bash
ls -l "/absolute/path/to/resume.pdf"
```

`Profile is slow`: profile extraction is an OpenAI call. Later runs should use the profile cache unless the resume changed.

`Greenhouse requires login`: complete the login in the persistent browser window and rerun the scan. FoxPilot does not bypass authentication or access controls.

`Database connection refused`: leave `DATABASE_URL` empty for local SQLite. A PostgreSQL URL requires a running PostgreSQL service, normally provided by Docker.

## Other Deployment Modes

- `docs/operations/LOCAL_AI.md`: provider-specific Ollama/OpenAI details.
- `docs/operations/RUN_MODES.md`: local CLI, Docker web, source, and containerized Ollama layouts.
- `docs/operations/DEPLOYMENT.md`: deployment and environment operations.
- `docs/operations/SECURITY_AND_PRIVACY.md`: data handling and production security.
