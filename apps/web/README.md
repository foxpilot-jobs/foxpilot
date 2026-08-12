# Career Agent Web App

The production web client will be a React, TypeScript, Vite, and responsive PWA application in this directory.

It will communicate only with the versioned FastAPI service under `services/api`. It must not import Python code, access SQLite, call Ollama, or scrape job sources directly.

The app will be added after the API contract and durable storage model stabilize. Until then, this file records the monorepo boundary without introducing a second source of business logic.
