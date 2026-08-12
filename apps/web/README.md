# FoxPilot Web App

The production web client will be a React, TypeScript, Vite, and responsive PWA application in this directory.

It will communicate only with the versioned FastAPI service under `services/api`. It must not import Python code, access SQLite, call Ollama, or scrape job sources directly.

The initial responsive shortlist experience is implemented in `src/`. It remains intentionally narrow while the API and hosted security model mature; new workflows must consume versioned API endpoints rather than adding business logic to the browser.

## Local Development

The current Vite/Babel release requires Node 22.18 or newer.

```bash
node --version
```

If using `nvm`, run `nvm use` from the repository root. Otherwise install Node 22 LTS before running the bootstrap script.

From the repository root:

```bash
./scripts/bootstrap-web.sh
cd apps/web
npm run dev
```

The script explicitly selects the public npm registry because environment-level npm configuration can override `.npmrc`.
