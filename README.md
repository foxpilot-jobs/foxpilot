# Career Agent

Career Agent is a local-first, open-source job discovery and decision-support tool. It helps a job seeker turn a resume and career goals into a focused list of relevant opportunities, with transparent explanations for every recommendation.

The working title is intentionally temporary. The product name and visual identity will be selected after the core user workflow is validated.

## Product Goal

Reduce the time and uncertainty between discovering a job and deciding whether it deserves an application.

The primary product metric is **qualified opportunities reviewed per hour of user effort**. Career Agent is not an auto-apply bot. The user remains in control of applications, communication, and personal data.

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
- Ollama with a local open model as the default LLM
- Optional OpenAI provider
- `httpx` and BeautifulSoup for static sources
- Playwright only when browser automation is necessary
- pytest, Ruff, and strict type checking
- GitHub Actions for quality gates
- Optional Streamlit dashboard after the CLI workflow is stable

## Status

The current repository is a proof of concept containing a working scraper, heuristic filter, and AI matcher. Production implementation is being built phase by phase. The current personal resume may remain on the maintainer's local machine as a temporary integration-test input, but it is ignored and must never be committed.

See:

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
career-agent init
career-agent scan
```

The bootstrap script selects public PyPI explicitly and the repository `.npmrc` selects the public npm registry. This avoids relying on machine-level package-manager configuration.

For local AI, install Ollama separately and pull the configured model. Remote providers are optional and may incur costs.

The current `scan` command is a compatibility entry point over the prototype pipeline. It still uses the existing Greenhouse browser flow and OpenAI matcher; those internals are being migrated behind the documented interfaces in later phases.

## Job Sources

Sources are planned as independent adapters. Greenhouse and Lever are the first structured ATS targets, followed by RemoteOK, Remotive, and Hacker News hiring threads. LinkedIn and Indeed are optional, higher-risk integrations whose availability and permitted access can change. The project will not promise unrestricted scraping or bypass access controls.

## License

Career Agent is released under the MIT License. See [LICENSE](LICENSE).
