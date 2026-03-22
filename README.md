# HRMS AI Service

AI-powered backend service for natural language interaction with HRMS data and company policy documents.

## What This Service Does

This project lets users ask HR questions in natural language and get answers from:

- Live HRMS APIs (employee, department, attendance, etc.)
- Policy documents via Retrieval-Augmented Generation (RAG)

It supports:

- Query intent classification (policy vs API data)
- Tool/API selection using semantic matching
- Policy retrieval from vector database
- Response generation with local LLM (Ollama)
- Redis caching
- Source attribution in responses

## Key Features

- Natural language chat endpoint: `POST /chat`
- Health endpoint: `GET /health`
- Policy retrieval using ChromaDB + embeddings
- API orchestration pipeline for data queries
- Source attribution for both policy and API responses
- Frontend chat UI with formatted source badges
- Local-first setup (Ollama + Redis + FastAPI)

## Tech Stack

- Python 3.11+
- FastAPI
- Uvicorn
- Ollama (default model from env)
- ChromaDB
- sentence-transformers
- Redis
- requests

## End-to-End Request Flow

1. User sends a question to `POST /chat`.
2. System checks Redis cache.
3. Query is routed by intent.
4. If policy query:
   - Retrieve relevant chunks from vector DB.
   - Build context and generate answer.
   - Extract policy source metadata.
5. If data query:
   - Classify domain and extract entities.
   - Select best API/tool using planner.
   - Execute HRMS API request.
   - Parse and generate final answer.
   - Capture API source metadata.
6. Return response with:
   - `answer` (final text)
   - `source` (formatted source attribution when available)
7. Save to Redis cache.

## Source Attribution Behavior

The service includes source attribution for transparency.

### Policy Query Response

- Source format: `Source: <PolicyName>`
- Example: `Source: Holiday_Policy`

### API Query Response

- Source format: `Source: <HTTP_METHOD> <ENDPOINT>`
- Example: `Source: GET /api/Department`

### Response Shape

```json
{
  "answer": "...answer text...\n\nSource: Holiday_Policy",
  "source": "Source: Holiday_Policy"
}
```

```json
{
  "answer": "...answer text...\n\nSource: GET /api/Department",
  "source": "Source: GET /api/Department"
}
```

### Notes

- Source is available as a dedicated `source` field.
- Source may also appear appended in `answer` depending on flow and cache behavior.
- If source is unavailable, `source` can be `null`.

## API Endpoints

### `GET /health`

Basic health check.

Example response:

```json
{
  "status": "ok"
}
```

### `POST /chat`

Main query endpoint.

Request:

```json
{
  "question": "Show me the departments in the company"
}
```

Possible response:

```json
{
  "answer": "The company has the following departments: ...\n\nSource: GET /api/Department",
  "source": "Source: GET /api/Department"
}
```

## Setup and Run

## Prerequisites

- Python 3.11+
- Redis server
- Ollama installed and running

## Installation

```bash
cd /Users/shyam_manohar/Desktop/Nighwan\ Tech/hrms_ai_service
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Start Required Services

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

## Verify

```bash
curl http://localhost:8000/health
```

## Query Test

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the company policies for holidays?"}'
```

## Configuration

Set values in `.env` (or your configured environment source):

- `OLLAMA_URL`
- `LLM_MODEL`
- `EMBED_MODEL`
- `CHROMA_PATH`
- `HRMS_API_BASE_URL`
- `HRMS_API_TOKEN`
- `REDIS_HOST` (optional, default: `localhost`)
- `REDIS_PORT` (optional, default: `6379`)

API selection tuning (optional):

- `SEMANTIC_SEARCH_K` (default: `10`)
- `KEYWORD_WEIGHT` (default: `0.5`)
- `SIMILARITY_THRESHOLD` (default: `0.2`)
- `REQUIRE_HIGH_CONFIDENCE` (default: `true`)

Notes:

- The service resolves `.env` from project root, so scripts work even if run from `scripts/`.
- After changing selection values, restart the API service.

## Logging Behavior

The terminal logs are intentionally concise. Typical lines include:

- `RAG Cache HIT` / `RAG Cache MISS`
- `Agent Cache HIT` / `Agent Cache MISS`
- `Query route: policy|data`
- `[ToolExecutor] Calling: <full-url>`
- Uvicorn access log lines for request status

API planner diagnostics (when selection goes through ranking/LLM):

- `Auto-selected (high confidence): <tool_name> ...`
- `LLM candidates: [...]`
- `LLM selected: <tool_name>`

## Frontend Behavior and Formatting

The chat UI in `app/static/chat-ui.html` is configured to:

- Preserve line breaks using `white-space: pre-wrap`
- Wrap long words and lines cleanly
- Display source attribution separately from answer content
- Show source badges:
  - Policy source style (green)
  - API source style (orange)

Formatting logic separates `answer` text from embedded `\n\nSource:` and renders source in a dedicated source section.

## Folder Structure (Detailed)

```text
hrms_ai_service/
├── app/
│   ├── config.py
│   ├── main.py
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py
│   │   │   └── health.py
│   │   └── schemas/
│   │       ├── chat_schema.py
│   │       └── response_schema.py
│   ├── cache/
│   │   └── redis_cache.py
│   ├── core/
│   │   ├── agent_router.py
│   │   ├── context_builder.py
│   │   ├── domain_classifier.py
│   │   ├── entity_extractor.py
│   │   ├── intent_classifier.py
│   │   ├── policy_service.py
│   │   ├── query_router.py
│   │   ├── rag_engine.py
│   │   ├── tool_executor.py
│   │   ├── tool_planner.py
│   │   └── tool_validator.py
│   ├── embeddings/
│   │   ├── chunking.py
│   │   └── embedding_model.py
│   ├── llm/
│   │   ├── llama_client.py
│   │   ├── prompts.py
│   │   └── response_parser.py
│   ├── services/
│   │   └── hrms_api_client.py
│   ├── static/
│   │   └── chat-ui.html
│   ├── tools/
│   │   └── api_registry.json
│   └── vectordb/
│       ├── api_vector_store.py
│       ├── chroma_client.py
│       └── retriever.py
├── chroma_db/
│   ├── chroma.sqlite3
│   ├── 3cabfcf0-d70d-4cc9-96fb-dda96effed2d/
│   └── 599433f8-572a-4ec7-b9cb-e453a33b4539/
├── scripts/
│   ├── build_registry.py
│   └── index_api_registry.py
├── dump.rdb
├── requirements.txt
├── README.md
└── venv/
```

## Folder and File Responsibilities

### `app/`

Main application package.

- `config.py`: Central configuration and environment loading.
- `main.py`: FastAPI app initialization and router inclusion.

### `app/api/routes/`

HTTP endpoints.

- `chat.py`: Accepts user questions and returns answer + source.
- `health.py`: Service health endpoint.

### `app/api/schemas/`

Pydantic request/response models.

- `chat_schema.py`: Chat request schema.
- `response_schema.py`: Chat response schema including optional `source`.

### `app/core/`

Core orchestration and intelligence pipeline.

- `rag_engine.py`: Top-level query orchestration.
- `query_router.py`: Chooses query path.
- `intent_classifier.py`: Intent detection.
- `domain_classifier.py`: Domain categorization.
- `entity_extractor.py`: Extracts IDs/names/entities from text.
- `policy_service.py`: Policy retrieval and source extraction.
- `agent_router.py`: Data query pipeline and API source capture.
- `tool_planner.py`: Selects likely tools/APIs.
- `tool_validator.py`: Validates selected tools.
- `tool_executor.py`: Executes selected tool/API operations.
- `context_builder.py`: Builds context for generation.

### `app/embeddings/`

Embedding and chunk preparation.

- `embedding_model.py`: Embedding model loading/inference.
- `chunking.py`: Splits long text into retrievable chunks.

### `app/llm/`

LLM integration.

- `llama_client.py`: Ollama client wrapper.
- `prompts.py`: Prompt templates.
- `response_parser.py`: Output parsing and formatting helpers.

### `app/vectordb/`

Vector DB connectivity and retrieval.

- `chroma_client.py`: ChromaDB client setup.
- `api_vector_store.py`: Indexing/search for API tools.
- `retriever.py`: Document retrieval, optional metadata return.

### `app/cache/`

Caching layer.

- `redis_cache.py`: Redis read/write and TTL behavior.

### `app/services/`

External integrations.

- `hrms_api_client.py`: Calls HRMS backend APIs with auth.

### `app/tools/`

Tool registry artifacts.

- `api_registry.json`: API metadata for planner/retrieval.

### `app/static/`

Frontend assets.

- `chat-ui.html`: Main and only chat UI.

### `scripts/`

Utility scripts for registry creation/indexing.

- `build_registry.py`: Builds tool registry from API definitions.
- `index_api_registry.py`: Pushes API registry data into vector index.

### `chroma_db/`

Local Chroma persistence directory.

- `chroma.sqlite3` and collection directories store vector data.

### `dump.rdb`

Redis snapshot file.

### `venv/`

Local virtual environment (dependencies and third-party files).

## Common Commands

## Activate Environment

```bash
source venv/bin/activate
```

## Run Server

```bash
uvicorn app.main:app --reload
```

## Rebuild API Registry (if APIs changed)

```bash
python scripts/build_registry.py
python scripts/index_api_registry.py
```

Alternative from inside `scripts/`:

```bash
python build_registry.py
python index_api_registry.py
```

## Open Swagger Docs

- http://localhost:8000/docs

## Troubleshooting

- `zsh: command not found: rg`
  - Install ripgrep or use `find` as fallback.
- `Connection refused` on `/chat`
  - Ensure `uvicorn` is running on expected port.
- Empty/weak answers for policy queries
  - Verify policy data is indexed in ChromaDB.
- API-related errors
  - Check `HRMS_API_BASE_URL` and `HRMS_API_TOKEN`.
- Slow first response
  - First LLM/embedding call is usually slower due to warm-up.

## Current Documentation Policy

All project documentation is consolidated into this single `README.md`.
Separate project Markdown docs were removed to keep one canonical source of truth.
