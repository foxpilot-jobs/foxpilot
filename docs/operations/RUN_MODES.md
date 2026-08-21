# Run Modes

FoxPilot currently supports three distinct run modes. They are not the same process layout.

## Local CLI

Everything runs on the host machine:

```text
foxpilot CLI -> SQLite (~/.foxpilot) -> host Ollama
                         |
                    host Playwright
```

Use this for the simplest private workflow. Profile extraction is cached against the configured resume path and content, so repeating `create_profile` or scanning does not invoke the LLM unless the resume changes:

```bash
source .venv/bin/activate
foxpilot scan
```

## Local Web With Docker

The current Compose setup is hybrid:

```text
Host Ollama :11434
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

- Ollama on `localhost:11434`.
- The interactive Playwright browser and `foxpilot scan`.

Start the host model first, then Compose:

```bash
# Terminal 1
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# Terminal 2
docker compose up --build -d

# Terminal 3
source .venv/bin/activate
./scripts/scan-docker.sh
```

The wrapper calls `.venv/bin/foxpilot` directly, so shell activation is optional after `./scripts/bootstrap.sh` has completed.

Open `http://localhost:8080` after the scan completes.

## Job Sources

`foxpilot scan` derives Greenhouse and public-source queries from the saved profile before fetching. A scan cannot run without a profile; there is no hardcoded role fallback. Source adapters filter profile-derived candidates before persistence, and match prompts omit raw source payloads and cap job descriptions to keep local inference bounded. The web profile page exposes the same profile-driven scan for authenticated public-source ingestion, while Greenhouse browser ingestion remains available through the local CLI because it requires the saved host browser session.

Ollama can run in Docker with `docker compose --profile container-llm up -d ollama`. To reuse an existing host model cache instead of downloading models again, set `OLLAMA_DATA_PATH=$HOME/.ollama` before starting the service. On macOS, native Ollama generally performs better because it can use Apple Metal; Docker Ollama is primarily an isolation/deployment option unless the host provides a Linux GPU passthrough.

- RemoteOK is enabled by default and reads its documented public feed.
- Remotive is enabled by default and searches the profile-derived role queries.
- Hacker News is enabled by default and filters public `Ask HN: Who is hiring?` comments with profile-derived role queries.
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

For hosted web profile setup, open `/app/profile` after signing in. Uploading a PDF stores extracted resume text and immediately returns a background job ID; profile extraction continues asynchronously. Use `Scan profile-specific jobs` to fetch public-source jobs using that account's saved roles, then use `Run matching` to queue analysis of the resulting profile-specific shortlist. The UI polls job status and shows completed results on `/app` sorted by match score, without holding the browser request open.

## Google Sign-In

Create a Google OAuth web application and add this authorized redirect URI for local Docker:

`http://localhost:8080/api/v1/auth/google/callback`

Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in the Compose environment. `GOOGLE_REDIRECT_URI` may override the default. The API validates the authorization state, exchanges the code server-side, verifies the Google ID token, links an existing email account when applicable, and creates the normal FoxPilot session cookie.

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
