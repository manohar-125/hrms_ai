# HRMS AI Service

Production-oriented FastAPI service that answers HRMS questions using:
- live HRMS APIs
- policy retrieval (RAG)
- local LLM generation via Ollama

---

## What This Service Provides

- `POST /chat` for natural-language Q&A
- `GET /health` for liveness
- API-source attribution (`Source: GET /api/...`)
- policy-source attribution (`Source: <PolicyName>`)
- Redis caching for repeated questions
- deterministic routing rules for sensitive cases:
  - personal attributes (email/mobile/blood group/religion/etc.) -> Employee Personal Details API
  - detection intents (vehicle/plate/face/object/dress) -> corresponding vision APIs

---

## Architecture Overview

### Request Flow

1. Client sends question to `POST /chat`.
2. `rag_engine` routes query to policy path or data/API path.
3. For data/API path:
   - `tool_planner` selects tool
   - `tool_validator` validates selected tool
   - `tool_executor` calls HRMS API
   - `agent_router` post-filters name-based results when needed
4. `llama_client` converts raw JSON response to natural-language answer.
5. Response is returned with `answer` + `source`.
6. Result is cached in Redis.

---

## API Registry (Source of Truth)

Registry file: `app/tools/api_registry.json`  
Build script: `scripts/build_registry.py`

### Current Rules

- Source Swagger: `https://hrmsapi.leanxpert.in/swagger/v1/swagger.json`
- Include all endpoints where:
  - path starts with `/api/`
  - method is `GET`
- Preserve exact endpoint casing (example: `/api/DressDetect`)
- No filtering by tag naming, operationId style, or unusual spelling
- Validation is mandatory during build:
  - compares Swagger GET `/api/*` count vs generated registry count
  - fails build if endpoints are missing

### Rebuild Command

```bash
python3 scripts/build_registry.py
```

---

## Setup

### Prerequisites

- Python 3.11+
- Redis
- Ollama

### Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Start Services

Terminal 1:
```bash
ollama serve
```

Terminal 2:
```bash
redis-server
```

Terminal 3:
```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

### Quick Check

```bash
curl http://localhost:8000/health
```

---

## Configuration (`.env`)

Required/important keys:

- `OLLAMA_URL`
- `LLM_MODEL`
- `EMBED_MODEL`
- `CHROMA_PATH`
- `HRMS_API_BASE_URL`
- `HRMS_API_TOKEN`
- `HRMS_API_VERIFY_SSL` (defaults to `false` for the current self-signed HRMS chain)
- `HRMS_API_TIMEOUT`
- `REDIS_HOST`
- `REDIS_PORT`

Optional API-selection tuning:

- `SEMANTIC_SEARCH_K`
- `KEYWORD_WEIGHT`
- `SIMILARITY_THRESHOLD`
- `REQUIRE_HIGH_CONFIDENCE`

---

## Response Format

```json
{
  "answer": "...\n\nSource: GET /api/EmpPersDtls",
  "source": "Source: GET /api/EmpPersDtls"
}
```

`source` may be `null` if attribution is unavailable.

---

## Important Routing Behavior

### Personal Details Routing

Queries asking personal attributes (e.g. email/mobile/blood group/religion/father name) with name/employee context are forced to Employee Personal Details API (`/api/EmpPersDtls`) to avoid misrouting to unrelated APIs.

### Vision Detection Routing

Queries with detection intent are short-circuited to vision APIs:

- vehicle/plate -> `/api/VechileDetect`
- face -> `/api/FaceDetect`
- object -> `/api/ObjectDetect`
- dress -> `/api/DressDetect`

---

## Project Structure

```text
hrms_ai_service/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   └── schemas/
│   ├── cache/
│   ├── core/
│   ├── embeddings/
│   ├── llm/
│   ├── services/
│   ├── static/
│   ├── tools/
│   │   └── api_registry.json
│   ├── vectordb/
│   ├── config.py
│   └── main.py
├── scripts/
│   └── build_registry.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## Cleanup Policy

This repository keeps production code and required generated artifacts only.

Removed as non-production/debug artifacts:
- `analyze_registry.py`
- `debug_api_selection.py`
- `test_api_selection.py`
- `app/tools/api_registry_full.json`

If temporary debug scripts are created in future, keep them out of mainline unless converted into proper tests under a dedicated test suite.

---

## Troubleshooting

- `Sorry, I could not find a suitable HRMS API for this query`
  - rebuild registry: `python3 scripts/build_registry.py`
  - restart service after config/routing changes
- First request is slow
  - embedding/LLM warm-up is expected
- API auth failures
  - verify `HRMS_API_BASE_URL` and `HRMS_API_TOKEN`
- HTTPS certificate verification errors
  - set `HRMS_API_VERIFY_SSL=false` when the upstream uses a self-signed certificate chain
- Ollama read timeouts
  - the service now trims large API payloads before summarization, but you can also raise `OLLAMA_TIMEOUT` if the local model is slow
- Redis connection error
  - ensure `redis-server` is running and `.env` host/port match
