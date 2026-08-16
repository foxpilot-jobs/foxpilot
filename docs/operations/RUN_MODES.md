# Run Modes

FoxPilot currently supports three distinct run modes. They are not the same process layout.

## Local CLI

Everything runs on the host machine:

```text
foxpilot CLI -> SQLite (~/.foxpilot) -> host Ollama
                         |
                    host Playwright
```

Use this for the simplest private workflow:

```bash
source .venv/bin/activate
foxpilot scan
```

## Local Web With Docker

The current Compose setup is hybrid:

```text
Host Ollama :11435
        ^
        |
Docker API -> Docker PostgreSQL
        ^
        |
Docker Nginx/Web :8080

Host foxpilot scan -> Docker PostgreSQL
```

Docker runs:

- PostgreSQL on `localhost:5432`.
- FastAPI on `localhost:8000`.
- Nginx-served React web app on `localhost:8080`.

The host runs:

- Ollama on `localhost:11435`.
- The interactive Playwright browser and `foxpilot scan`.

Start the host model first, then Compose:

```bash
# Terminal 1
OLLAMA_HOST=0.0.0.0:11435 ollama serve

# Terminal 2
docker compose up --build -d

# Terminal 3
source .venv/bin/activate
./scripts/scan-docker.sh
```

The wrapper calls `.venv/bin/foxpilot` directly, so shell activation is optional after `./scripts/bootstrap.sh` has completed.

Open `http://localhost:8080` after the scan completes.

## Job Sources

`foxpilot scan` runs the saved Greenhouse browser searches plus the public adapters configured in `data/sources.json`.

- RemoteOK is enabled by default and reads its documented public feed.
- Remotive is enabled by default and searches the configured query list.
- Hacker News is enabled by default and reads public `Ask HN: Who is hiring?` comments.
- Lever is enabled when board slugs are added under `lever.boards`, for example:

```json
{
  "lever": {
    "boards": [
      {"slug": "example-company", "company": "Example Company"}
    ]
  }
}
```

Use `FOXPILOT_SOURCES_CONFIG=/path/to/sources.json` for a separate configuration. Each source is deduplicated through the shared database and a failed source does not stop the rest of the scan.

## Fully Containerized Ollama

The Compose file includes an optional `container-llm` profile:

```bash
```

Use this only when the Docker Ollama image has a valid certificate chain for `registry.ollama.ai`. On enterprise networks, install the approved CA into a derived Ollama image. Do not disable TLS verification in a hosted deployment.

## Enterprise Docker Proxy

Docker Desktop may route container traffic through an enterprise HTTPS proxy. Docker Hub pulls can succeed while Ollama registry pulls fail with `x509: certificate signed by unknown authority`. This means the proxy CA is missing from the Ollama container, not that the model or FoxPilot configuration is invalid.

The supported local workaround is host Ollama, which uses the host trust store. The secure containerized fix requires the approved enterprise CA certificate to be installed in a derived Ollama image. Do not copy credentials or private registry configuration into this repository.

## Stop And Data

```bash
```

This stops containers but preserves PostgreSQL and Ollama volumes. `docker compose down -v` deletes those volumes and is destructive.
