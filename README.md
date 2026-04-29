# HRMS AI Service

Local-first FastAPI service for HRMS question answering. The main branch is configured around a **local Ollama runtime**, live HRMS APIs, Redis caching, and a small policy/document RAG path.

This service answers employee and HR questions by routing each request to the best source:
- HRMS REST APIs for live operational data
- policy retrieval for document-style questions
- Ollama for natural-language response generation

---

## What This Service Does

- Serves a chat endpoint at `POST /chat`
- Serves a health endpoint at `GET /health`
- Exposes a browser chat UI at `/`
- Routes detection queries to vision APIs such as face, dress, object, and vehicle detection
- Uses Redis to cache repeated questions
- Uses local Ollama to turn raw API responses into readable answers
- Returns source attribution when available

---

## High-Level Workflow

1. A user sends a question to `POST /chat` or the web UI.
2. The request enters the RAG engine.
3. The request is classified as either:
   - policy/document question, or
   - data/API question
4. For policy questions:
   - the service retrieves policy context
   - Ollama turns the retrieved context into an answer
5. For data/API questions:
   - the tool planner picks the best HRMS endpoint
   - the tool validator confirms the tool is valid
   - the tool executor calls the HRMS API
   - the Ollama client summarizes the JSON response
6. The answer is returned with optional source metadata.
7. The final answer is cached in Redis for repeated requests.

---

## Runtime Components

- FastAPI application: `app/main.py`
- Chat route: `app/api/routes/chat.py`
- Health route: `app/api/routes/health.py`
- RAG entry point: `app/core/rag_engine.py`
- Tool planning and routing: `app/core/tool_planner.py`, `app/core/tool_validator.py`, `app/core/agent_router.py`
- HRMS HTTP client: `app/services/hrms_api_client.py`
- Ollama client: `app/llm/llama_client.py`
- Redis cache: `app/cache/redis_cache.py`
- API registry: `app/tools/api_registry.json`
- Registry build script: `scripts/build_registry.py`

---

## Local Workflow

### 1. Start prerequisites

You need these services running locally:
- Redis
- Ollama
- the FastAPI app itself

### 2. Configure environment

Create or update your `.env` with the required settings.

### 3. Start services in this order

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

### 4. Verify the app

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"ok"}
```

### 5. Send a chat request

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"show face detection history"}'
```

---

## API Endpoints

### `GET /health`
Returns a simple liveness check.

### `POST /chat`
Body:
```json
{
  "question": "show dress detection history"
}
```

Response:
```json
{
  "answer": "...",
  "source": "Source: GET /api/DressDetect"
}
```

### `GET /`
Serves the static chat UI if `app/static/chat-ui.html` exists.

---

## Request Routing Behavior

### Policy Questions

Questions about policy documents are routed through the policy retrieval path.

### HRMS Data Questions

Operational questions are routed through the HRMS API registry and planner.

### Personal Details Routing

Queries asking for personal attributes such as:
- email
- mobile number
- blood group
- religion
- father name
- profile details

are biased toward the employee personal details API to avoid misrouting.

### Vision Detection Routing

Detection-oriented queries are short-circuited to the matching vision endpoint:

- vehicle / plate -> `/api/VechileDetect`
- face -> `/api/FaceDetect`
- object -> `/api/ObjectDetect`
- dress -> `/api/DressDetect`

That means queries like these should work naturally:
- show face detection history
- give me dress detection history
- show object detection history
- show vehicle detection history
- fetch recent face detections
- get latest dress detection records

---

## Local Ollama Behavior

This branch uses a local Ollama instance for answer generation.

Important notes:
- `OLLAMA_URL` must point to your local Ollama server, usually `http://localhost:11434`
- `LLM_MODEL` must match a model available in your local Ollama installation
- API responses are trimmed before being sent to Ollama so large histories do not overwhelm the prompt
- Ollama timeout is configurable through `OLLAMA_TIMEOUT`

If Ollama is slow or not running, the service will return an LLM service error instead of hanging forever.

---

## HRMS API Behavior

The service talks to the upstream HRMS API for live data.

Important runtime settings:
- `HRMS_API_BASE_URL`
- `HRMS_API_TOKEN`
- `HRMS_API_VERIFY_SSL`
- `HRMS_API_TIMEOUT`

TLS note:
- the current main branch defaults `HRMS_API_VERIFY_SSL` to `false` because the upstream chain can present a self-signed certificate chain in local/dev environments
- if your upstream is trusted by your machine, you can turn it back on

---

## Configuration

### Required settings

- `OLLAMA_URL`
- `LLM_MODEL`
- `EMBED_MODEL`
- `CHROMA_PATH`
- `HRMS_API_BASE_URL`
- `HRMS_API_TOKEN`

### Runtime settings with defaults

- `HRMS_API_VERIFY_SSL=false`
- `HRMS_API_TIMEOUT=30`
- `OLLAMA_TIMEOUT=120`
- `LLM_MAX_API_ITEMS=50`
- `LLM_MAX_API_RESPONSE_CHARS=12000`
- `REDIS_HOST=localhost`
- `REDIS_PORT=6379`

### Optional API-selection tuning

- `SEMANTIC_SEARCH_K`
- `KEYWORD_WEIGHT`
- `SEMANTIC_WEIGHT`
- `INTENT_WEIGHT`
- `SIMILARITY_THRESHOLD`
- `REQUIRE_HIGH_CONFIDENCE`

### Example `.env`

```bash
OLLAMA_URL=http://localhost:11434
LLM_MODEL=llama3.1
EMBED_MODEL=all-MiniLM-L6-v2
CHROMA_PATH=./chroma_db

HRMS_API_BASE_URL=https://hrmsapi.leanxpert.in
HRMS_API_TOKEN=your-token-here
HRMS_API_VERIFY_SSL=false
HRMS_API_TIMEOUT=30

REDIS_HOST=localhost
REDIS_PORT=6379

OLLAMA_TIMEOUT=120
LLM_MAX_API_ITEMS=50
LLM_MAX_API_RESPONSE_CHARS=12000
```

---

## Setup

### Prerequisites

- Python 3.11+
- Redis
- Ollama
- a model pulled into Ollama, for example `llama3.1`

### Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Pull an Ollama model

```bash
ollama pull llama3.1
```

If you use a different model, update `LLM_MODEL` in `.env`.

### Start the app

```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

---

## Detailed Request Flow

### Chat request flow

1. The client submits a question.
2. `app/core/rag_engine.py` checks Redis cache.
3. If the question is cached, the answer is returned immediately.
4. Otherwise the engine decides whether the request is policy-related or data-related.
5. For data requests, `app/core/agent_router.py` handles tool selection and API execution.
6. The HRMS response is passed to `app/llm/llama_client.py`.
7. Ollama converts the raw response into a short natural-language answer.
8. The answer is stored in Redis.
9. The response is returned with source metadata when available.

### Tool execution flow

1. `app/core/tool_planner.py` chooses the best endpoint from `app/tools/api_registry.json`.
2. `app/core/tool_validator.py` checks the tool exists and has the expected shape.
3. `app/core/tool_executor.py` performs the HTTP request.
4. `app/llm/llama_client.py` summarizes the response using local Ollama.

---

## API Registry

The registry file is the source of truth for HRMS endpoints:
- `app/tools/api_registry.json`

The build script that generates it is:
- `scripts/build_registry.py`

Current registry rules:
- include `GET` endpoints under `/api/`
- preserve exact casing
- keep vision endpoints such as `/api/FaceDetect` and `/api/DressDetect`
- validate the generated registry against the source swagger data

To rebuild the registry:
```bash
python3 scripts/build_registry.py
```

---

## Example Queries

### Dress detection
- show dress detection history
- give me dress detection history
- fetch latest dress detection records
- show recent clothing detection entries

### Face detection
- show face detection history
- give me face detection history
- fetch latest face detection records
- show recent facial recognition entries

### Object detection
- show object detection history
- give me object detection history
- fetch latest object detection records
- show recent item detection entries

### Vehicle detection
- show vehicle detection history
- give me vehicle detection history
- fetch latest vehicle detection records
- show recent number plate detection entries

### Other HRMS queries
- show employee attendance for today
- get leave balance for John Doe
- show payroll details for employee 1024
- fetch personal details for employee 1088

---

## Response Format

The chat endpoint returns:

```json
{
  "answer": "The latest face detection records are ...",
  "source": "Source: GET /api/FaceDetect"
}
```

`source` may be `null` when the system cannot attach a reliable source label.

---

## Troubleshooting

### `certificate verify failed` for HRMS APIs
Set:
```bash
HRMS_API_VERIFY_SSL=false
```
This is the common fix when the upstream presents a self-signed certificate chain.

### `LLM service error: HTTPConnectionPool(host='localhost', port=11434): Read timed out`
- make sure `ollama serve` is running
- confirm the model in `LLM_MODEL` exists locally
- increase `OLLAMA_TIMEOUT` if the model is slow
- reduce prompt size by keeping `LLM_MAX_API_ITEMS` and `LLM_MAX_API_RESPONSE_CHARS` reasonable

### `Sorry, I could not find a suitable HRMS API for this query`
- rebuild the registry
- restart the app after registry or routing changes
- confirm the query is close to a supported endpoint

### Redis connection errors
- ensure `redis-server` is running
- confirm `REDIS_HOST` and `REDIS_PORT`

### First request feels slow
This is normal the first time after startup because the app may warm the LLM, embeddings, and cache paths.

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
├── chroma_db/
├── scripts/
│   └── build_registry.py
├── tests/
├── requirements.txt
└── README.md
```

---

## Notes for Maintainers

- Keep the README aligned with the current local Ollama workflow on main.
- Update the configuration table whenever new runtime settings are added.
- If the API registry changes, keep the query examples in sync with the supported endpoints.
- When upstream certificate handling changes, revisit `HRMS_API_VERIFY_SSL` and this troubleshooting section.
