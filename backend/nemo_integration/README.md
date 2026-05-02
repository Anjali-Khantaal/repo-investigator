# Optional NeMo integration

This folder contains a minimal **NeMo Agent Toolkit custom function plugin** that wraps the running `repo-investigator` backend.

## Why it is structured this way

NeMo is excellent for orchestration, but it is more version-sensitive than the core FastAPI + DSPy app. So the main app is kept simple and stable, while the NeMo layer is isolated here.

## What it does

The custom NeMo function `repo_investigator` calls the backend API:

- endpoint: `POST /ask`
- input: a natural-language question
- output: the grounded answer text from the backend

That lets you use NeMo as an orchestration shell without duplicating the core analysis logic.

## Install

```bash
pip install -r requirements-nemo.txt
pip install -e backend/nemo_integration
```

## Run

1. Start the backend first:

```bash
bash scripts/run_backend.sh
```

2. Start NeMo:

```bash
nat serve --config_file backend/nemo_integration/config.yml
```

3. Send a request:

```bash
curl --request POST \
  --url http://localhost:8000/generate \
  --header 'Content-Type: application/json' \
  --data '{"input_message": "Where is authentication handled?"}'
```

## Notes

- The plugin registers under both `nat.components` and `nat.plugins` entry points to reduce version-friction across recent toolkit variants.
- The NeMo workflow uses a local OpenAI-compatible LLM configuration by default.
