# FoxPilot

FoxPilot is a local-first, open-source job discovery and decision-support tool. It helps a job seeker turn a resume and career goals into a focused list of relevant opportunities, with transparent explanations for every recommendation.

FoxPilot is the product identity for the current build.

## Product Goal

Reduce the time and uncertainty between discovering a job and deciding whether it deserves an application.

The primary product metric is **qualified opportunities reviewed per hour of user effort**. FoxPilot is not an auto-apply bot. The user remains in control of applications, communication, and personal data.

## Planned Workflow

1. Import a resume locally.
2. Configure target roles, locations, constraints, and preferences.
3. Discover jobs through independent source adapters.
4. Remove duplicates and irrelevant listings.
5. Rank opportunities against the user's profile.
6. Explain matching skills, gaps, risks, and next actions.
7. Track saved, applied, interviewing, rejected, and offered jobs.
8. Measure time saved and application outcomes.

## Principles

- Local-first: the default workflow runs on the user's machine.
- Open-source first: use free and open-source software wherever practical.
- Private by default: resume and career data stay local unless the user opts into a remote provider.
- Explainable: scores are evidence-backed suggestions, not hiring decisions.
- User-controlled: no application or outreach is sent without confirmation.
- Replaceable: LLMs, job sources, storage, and notifications use explicit interfaces.
- Sustainable: integrations must be documented, rate-limited, and compliant with source terms.

## Technology Direction

- Python 3.11+
- Typer CLI
- Pydantic domain models
- SQLite persistence
- SQLAlchemy repository with SQLite local default and PostgreSQL hosted option
- Alembic schema migrations
- Ollama with a local open model as the default LLM
- Optional OpenAI provider
- `httpx` and BeautifulSoup for static sources
- Playwright only when browser automation is necessary
- pytest, Ruff, and strict type checking
- GitHub Actions for quality gates
- Optional Streamlit dashboard after the CLI workflow is stable
- React + TypeScript + Vite web/PWA in `apps/web`
- FastAPI service layer in `services/api`

## Status

The current repository is a proof of concept containing a working scraper, heuristic filter, and AI matcher. Production implementation is being built phase by phase. The current personal resume may remain on the maintainer's local machine as a temporary integration-test input, but it is ignored and must never be committed.

See:

- [Setup guide](docs/operations/SETUP.md)
- [Product brief](docs/product/PRODUCT_BRIEF.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Architecture decisions](docs/architecture/DECISIONS.md)
- [Roadmap](docs/roadmap/ROADMAP.md)
- [Security and privacy](docs/operations/SECURITY_AND_PRIVACY.md)
- [Contributing](CONTRIBUTING.md)
- [Agent baseline](.agents/BASELINE.md)

## Local Development

The package and CLI migration are part of Phase 1. Until that work lands, the legacy scripts can be inspected under `src/`. Do not add new features to the legacy scripts without first updating the architecture documentation and migration plan.

The intended setup will be:

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
cp .env.example .env
foxpilot init
foxpilot scan
```

The bootstrap script selects public PyPI explicitly and the repository `.npmrc` selects the public npm registry. This avoids relying on machine-level package-manager configuration.

## Local AI With Ollama

Ollama is the default provider and keeps resume data on your machine:

```bash
brew install ollama
ollama serve
ollama pull llama3.1:8b
ollama list
```

Keep `ollama serve` running in a separate terminal. In `.env`, use:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b
```

Then run:

```bash
source .venv/bin/activate
foxpilot init --resume /absolute/path/to/resume.pdf
foxpilot migrate
foxpilot scan
```

The first local model request can take a few minutes. Ollama requires local compute and disk space, but no API key. OpenAI remains available as an explicit opt-in provider by setting `LLM_PROVIDER=openai`, `LLM_MODEL=<model>`, and `OPENAI_API_KEY` in `.env`.

See [Local AI](docs/operations/LOCAL_AI.md) for troubleshooting and provider behavior.

For a fresh machine using SQLite and OpenAI without Docker or Ollama, follow the [Setup guide](docs/operations/SETUP.md).

## Repository Shape

This is a monorepo by design. The Python domain and application services remain the source of truth. The web app is a separate React workspace under `apps/web`, and the API is a separate deployable service under `services/api`.

```text
foxpilot/
├── src/career_agent/       # Python domain, providers, sources, storage
├── services/api/           # FastAPI HTTP adapter over Python services
├── apps/web/               # React + TypeScript responsive PWA
├── tests/                  # Python unit and integration tests
└── docs/                   # Product, architecture, operations, roadmap
```

## Deployment Modes

- Local CLI: Python package, SQLite, and Ollama on the user's machine.
- Local web: hybrid Docker Compose with API, PostgreSQL, and web in Docker; Ollama and interactive scanning on the host.
- Hosted web: static React frontend, FastAPI service, PostgreSQL, and an explicitly configured LLM provider.

The local deployment is the privacy-preserving and lifetime-free baseline. Hosted deployment is optional and may require paid infrastructure.

For the web client, use the repository bootstrap script rather than a machine-level npm command:

```bash
./scripts/bootstrap-web.sh
cd apps/web
npm run dev
```

The web stack requires Node 22.18 or newer; Node 24.19 is the validated runtime. The repository includes `.nvmrc` with the recommended major version.

For the exact process layout, see [Run Modes](docs/operations/RUN_MODES.md). For deployment details, see [Deployment](docs/operations/DEPLOYMENT.md).

After starting Docker and host Ollama, run the integrated scan wrapper:

```bash
./scripts/scan-docker.sh
```

Run the API in another terminal:

```bash
source .venv/bin/activate
uvicorn services.api.app:app --reload --port 8000
```

Then open the web client at `http://localhost:5173`. The Vite development server proxies `/api` to the local API.

`~/.foxpilot/` is per-user local state. It is created automatically, is ignored by git, and is not copied when the repository is cloned. Existing `~/.career-agent/` state is read as a legacy fallback. Each machine needs its own `foxpilot init --resume ...` setup. This is intentional: resumes, browser sessions, job history, and match history must not be shared through source control.

## Job Sources

Sources are planned as independent adapters. Greenhouse and Lever are the first structured ATS targets, followed by RemoteOK, Remotive, and Hacker News hiring threads. LinkedIn and Indeed are optional, higher-risk integrations whose availability and permitted access can change. The project will not promise unrestricted scraping or bypass access controls.

## License

FoxPilot is released under the MIT License. See [LICENSE](LICENSE).
