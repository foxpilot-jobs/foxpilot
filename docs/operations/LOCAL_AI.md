# Local AI

## Default Provider

Career Agent uses Ollama by default. Profile extraction and job matching send prompts to the local Ollama HTTP API at `http://localhost:11434`. The application does not upload resume data when `LLM_PROVIDER=ollama`.

## macOS Setup

```bash
brew install ollama
ollama serve
ollama pull llama3.1:8b
```

Verify the model:

```bash
ollama list
```

The model name in `.env` must exactly match the installed model:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b
```

## Run Order

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
career-agent init --resume /absolute/path/to/resume.pdf
career-agent scan --dry-run
career-agent scan
```

The first real scan may open a browser for the configured job source. Ollama must remain running while profile extraction or matching is active.

## Troubleshooting

- `Ollama is not running`: run `ollama serve` in another terminal.
- `model not found`: run `ollama pull <model>` and make `.env` match it.
- Slow first response: local models may need time to load into memory.
- Out of memory: use a smaller model and set `LLM_MODEL` accordingly.
- Invalid JSON: the provider requests JSON mode and the application validates the response; retrying with a stronger model may help.

## Optional Hosted Provider

OpenAI is not required. If explicitly selected, configure:

```env
LLM_PROVIDER=openai
LLM_MODEL=<supported-model>
OPENAI_API_KEY=<local-secret>
```

Hosted providers can incur cost and may receive resume or job data. Use them only with that understanding.
