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

Open `http://localhost:8080` after the scan completes.

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
