# HRMS AI Service

FastAPI service for asking HR questions in natural language and answering them from live HRMS APIs or policy documents.

## Overview

The application routes each chat question into one of two paths:

- Policy questions use a RAG flow over ChromaDB-backed policy chunks.
- Data questions use an HRMS API selection and execution flow.

The response includes the final answer plus source attribution when available.

## What The Service Does

- Accepts chat requests at `POST /chat`.
- Serves a health check at `GET /health`.
- Serves the chat UI at `/` and static assets under `/static`.
- Classifies each question as policy or data.
- Uses Redis caching for repeated questions.
- Retrieves policy text from the HRMS API, chunks it, and stores it in ChromaDB.
- Selects the best HRMS API tool using domain filtering, keyword scoring, semantic search, and an LLM tie-breaker.
- Calls the selected HRMS API with the configured bearer token.
- Formats source attribution for both policy and API answers.

## Request Flow

1. A client sends `POST /chat` with a JSON body containing `question`.
2. `app/core/rag_engine.py` checks Redis cache first.
3. The question is classified by intent in `app/core/intent_classifier.py`.
4. `app/core/query_router.py` maps `policy` questions to the policy RAG path and all other intents to the data path.
5. Policy path:
   - `app/core/policy_service.py` fetches policy data from `/api/Policies`, then falls back to `/LeavePolicy`.
   - The best policy candidate is chosen using embedding similarity plus lexical overlap.
   - Existing Chroma chunks are queried first.
   - If no chunks exist, the policy is cleaned, chunked, embedded, and stored.
   - A prompt is built from the system prompt, conversation history, retrieved context, and question.
  - The configured LLM provider generates the final answer.
6. Data path:
   - `app/core/agent_router.py` checks its cache and then asks `app/core/tool_planner.py` for a tool.
   - `app/core/domain_classifier.py` narrows the registry to the most relevant domain.
   - `app/core/entity_extractor.py` extracts numeric IDs and employee names.
   - The planner combines registry keywords, semantic search from ChromaDB, and LLM selection when multiple candidates remain.
   - `app/core/tool_validator.py` verifies the chosen tool exists and has `endpoint` and `method`.
   - `app/core/tool_executor.py` performs the API call.
   - `app/llm/llama_client.py` turns the raw JSON payload into a natural-language answer.
7. The answer and source metadata are returned to the route handler.
8. The route appends source attribution to the answer and returns the `ChatResponse` payload.

## API Endpoints

### `GET /health`

Returns a simple health response:

```json
{
  "status": "ok"
}
```

### `POST /chat`

Request body:

```json
{
  "question": "Show me the departments in the company"
}
```

Response shape:

```json
{
  "answer": "The company has the following departments: ...\n\nSource: GET /api/Department",
  "source": "Source: GET /api/Department"
}
```

For policy answers, the source format becomes `Source: <PolicyName>` and may include a page number when available.

## Source Attribution

Source formatting is handled in `app/core/rag_engine.py` and returned through `app/api/routes/chat.py`.

- Policy sources use `Source: <PolicyName>` or `Source: <PolicyName> (Page <n>)`.
- API sources use `Source: <HTTP_METHOD> <ENDPOINT>`.
- The frontend separates embedded source text from the main answer and renders a dedicated source badge.

## UI

The built-in chat UI lives in `app/static/chat-ui.html` and is served at the app root.

- Dark, neon-styled layout with a grid background and glassmorphism panels.
- Uses `Inter` for body text and `Syne` for the title.
- Includes `Export PDF` and `Clear Chat` controls.
- Preserves line breaks with `white-space: pre-wrap`.
- Shows policy sources as green badges and API sources as orange badges.
- Uses a loading spinner while exporting to PDF.

## Runtime Components

### App startup

`app/main.py` creates the FastAPI application, includes the chat and health routers, mounts static files, and serves `chat-ui.html` from `/` when available.

### Configuration

`app/config.py` reads settings from `.env` in the project root.

Required variables:

- `LLM_PROVIDER`
- `EMBED_MODEL`
- `CHROMA_PATH`
- `HRMS_API_BASE_URL`
- `HRMS_API_TOKEN`
- `OPENAI_API_KEY`
- `GROQ_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`

Provider-specific model variables:

- `OPENAI_MODEL`
- `GROQ_MODEL`
- `ANTHROPIC_MODEL`
- `GEMINI_MODEL`

Optional variables:

- `REDIS_HOST` default: `localhost`
- `REDIS_PORT` default: `6379`
- `SEMANTIC_SEARCH_K` default: `10`
- `KEYWORD_WEIGHT` default: `0.5`
- `SIMILARITY_THRESHOLD` default: `0.2`
- `REQUIRE_HIGH_CONFIDENCE` default: `true`

### Caching

`app/cache/redis_cache.py` uses Redis when available and falls back to disabled caching if Redis cannot be reached. Keys are normalized to reduce duplicate cache entries.

### Conversation context

`app/core/context_builder.py` keeps in-memory conversation history only. It stores question/answer pairs per session and includes the last five exchanges in the prompt context.

### LLM integration

`app/llm/llm_factory.py` selects the active provider from `LLM_PROVIDER`.

`app/llm/providers/` contains the OpenAI, Groq, Anthropic, and Gemini implementations. The execution layer is used for:

- Free-form answer generation for policy queries.
- Natural-language conversion of API JSON responses.
- Intent and domain classification prompts.
- Tool selection tie-breaking when multiple APIs are plausible.

### Policy retrieval

`app/core/policy_service.py`:

- Fetches policies from the HRMS API.
- Accepts text fields, PDF URLs, base64 PDF payloads, and raw PDF bytes.
- Uses PyPDF, PyMuPDF, and Tesseract OCR when needed.
- Cleans repeated headers/footers and short noisy lines.
- Chunks policy text with 500-character chunks and 50-character overlap.
- Stores policy embeddings in the `hrms_documents` Chroma collection.

### API selection

`app/core/tool_planner.py`:

- Loads `app/tools/api_registry.json` on each request.
- Filters tools by domain.
- Prefers non-parameterized endpoints when the query does not look like an ID lookup.
- Applies special rules for personal-details and employee-list queries.
- Combines semantic similarity and keyword scoring.
- Falls back to LLM selection only when multiple candidates remain.

### API execution

`app/core/tool_executor.py` performs GET requests against the configured HRMS base URL and sends the bearer token in the `Authorization` header.

### HRMS API client

`app/services/hrms_api_client.py` wraps generic GET requests, fetches policies, and downloads binary policy files.

## Vector Store

The project uses ChromaDB for two separate collections:

- `hrms_documents` for policy chunks.
- `api_tools` for API registry search.

Embedding uses `sentence-transformers` with `BAAI/bge-small-en`.

`app/vectordb/api_vector_store.py` indexes registry entries as tool documents and supports semantic search with similarity scores.

`app/vectordb/retriever.py` queries policy chunks, optionally returning metadata.

## Registry Scripts

### `scripts/build_registry.py`

- Downloads the Swagger spec from `https://hrmsapi.leanxpert.in/swagger/v1/swagger.json`.
- Generates `app/tools/api_registry.json` from GET endpoints under `/api/`.
- Infers tool names, domains, keywords, parameters, and normalized intent metadata.

### `scripts/index_api_registry.py`

- Validates `app/tools/api_registry.json`.
- Syncs the registry into ChromaDB.
- Removes stale vector entries.
- Supports `--watch` mode for automatic re-sync on file changes.

## Project Structure

```text
hrms_ai_service/
├── app/
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
│   │   ├── api_selector.py
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
│   │   ├── base_llm.py
│   │   ├── llama_client.py
│   │   ├── llm_factory.py
│   │   ├── provider_utils.py
│   │   └── providers/
│   │       ├── anthropic_provider.py
│   │       ├── gemini_provider.py
│   │       ├── groq_provider.py
│   │       └── openai_provider.py
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
├── scripts/
│   ├── build_registry.py
│   └── index_api_registry.py
├── dump.rdb
├── requirements.txt
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+
- Redis server
- HRMS API access token and base URL
- At least one LLM provider key if you want to use OpenAI, Groq, Anthropic, or Gemini

### Install

```bash
cd /Users/shyam_manohar/Desktop/Nighwan\ Tech/hrms_ai_service
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Run

Terminal 1:

```bash
redis-server
```

Terminal 2:

```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

### Verify

```bash
curl http://localhost:8000/health
```

### Test a chat request

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the company policies for holidays?"}'
```

## Useful Commands

Activate the virtual environment:

```bash
source venv/bin/activate
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Rebuild and reindex the API registry:

```bash
python scripts/build_registry.py
python scripts/index_api_registry.py
```

Open the API docs:

- http://localhost:8000/docs

## Logging

The service logs are intentionally concise. Common messages include:

- `RAG Cache HIT` and `RAG Cache MISS`
- `Agent Cache HIT` and `Agent Cache MISS`
- `Query route: policy` or `Query route: data`
- `[ToolExecutor] Calling: <full-url>`
- `[LLM] Provider: <name>`
- `[LLM] Prompt tokens: <n>`
- `[LLM] Response time: <n> ms`
- `Auto-selected (high confidence): <tool_name>`
- `LLM candidates: [...]`
- `LLM selected: <tool_name>`

## Dependencies

Key packages from `requirements.txt`:

- FastAPI and Uvicorn
- requests
- redis
- chromadb
- sentence-transformers
- numpy and scipy
- pydantic and pydantic-settings
- pypdf, PyMuPDF, pytesseract, and Pillow

## Notes

- The app serves the chat UI at `/`, so opening the root URL is the quickest way to test the frontend.
- Conversation history is in-memory only and resets when the process restarts.
- Source may appear both in the `answer` text and in the dedicated `source` field.
- If Redis is unavailable, caching is disabled rather than blocking the service.
- All project documentation is consolidated into this single `README.md`.
