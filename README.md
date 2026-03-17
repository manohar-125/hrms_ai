# HRMS AI Service - Complete Documentation

**AI-powered backend system for natural language interaction with HRMS (Human Resource Management) systems.**

Enable users to query employee data and HR policies using natural language instead of navigating complex HRMS interfaces.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Prerequisites](#prerequisites)
6. [Installation & Setup](#installation--setup)
7. [Configuration](#configuration)
8. [API Documentation](#api-documentation)
9. [System Architecture](#system-architecture)
10. [Core Components](#core-components)
11. [Processing Pipeline](#processing-pipeline)
12. [Example Queries](#example-queries)
13. [Troubleshooting](#troubleshooting)
14. [Development](#development)

---

## Overview

**HRMS AI Service** is an intelligent backend that bridges natural language understanding with HRMS data retrieval. Users can ask questions in plain English, and the system:

✅ Classifies the query intent (policy lookup vs data retrieval)  
✅ Finds the best-matching HRMS APIs using semantic search  
✅ Retrieves relevant HR policy documents using RAG  
✅ Generates natural language responses using Ollama LLM  
✅ Caches results for improved performance  

### Example Questions

```
"Show employee 102"
"List all departments"
"What are the leave policies?"
"Show employee bank account details"
"List employees in the IT department"
"What is the maternity leave policy?"
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Natural Language Processing** | Understands user intent from plain English queries |
| **Intent Classification** | Distinguishes between policy queries (RAG) and data queries (API) |
| **Semantic Tool Selection** | Uses hybrid ranking (BM25 + embeddings) to find optimal HRMS APIs |
| **Policy RAG** | Vector database for storing/retrieving HR policy documents |
| **Multi-stage LLM** | Ollama-powered intent classification, entity extraction, response generation |
| **Redis Caching** | Caches frequent queries for improved response time |
| **Docker Deployment** | Easy deployment with Docker & Docker Compose |
| **API Registry** | Swagger-based HRMS API discovery and indexing |

---

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Python 3.11** - Core language
- **Uvicorn** - ASGI server

### AI & ML
- **Ollama** - Local LLM inference (default: Llama2)
- **ChromaDB** - Vector database for embeddings
- **sentence-transformers** - Text embeddings (BAAI/bge-small-en)
- **scikit-learn** - BM25 ranking algorithm

### Data & Cache
- **Redis** - Caching layer (600s TTL)
- **Requests** - HTTP client

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

---

## Project Structure

```
hrms_ai_service/
│
├── app/
│   ├── api/                          # REST API Routes
│   │   ├── routes/
│   │   │   ├── chat.py              # POST /chat endpoint
│   │   │   └── health.py            # GET /health endpoint
│   │   └── schemas/
│   │       ├── chat_schema.py       # ChatRequest, ChatResponse
│   │       └── response_schema.py   # Response models
│   │
│   ├── core/                        # Orchestration & Processing
│   │   ├── rag_engine.py            # Main pipeline orchestrator
│   │   ├── agent_router.py          # Data query processing pipeline
│   │   ├── query_router.py          # Intent-based routing
│   │   ├── policy_service.py        # Policy RAG retrieval
│   │   ├── context_builder.py       # Conversation context management
│   │   ├── tool_planner.py          # Hybrid tool/API selection
│   │   ├── tool_validator.py        # Tool validation
│   │   ├── tool_executor.py         # HRMS API execution
│   │   ├── intent_classifier.py     # Intent classification
│   │   ├── domain_classifier.py     # Domain identification
│   │   └── entity_extractor.py      # Entity extraction (IDs, names)
│   │
│   ├── llm/                         # Language Model Integration
│   │   ├── llama_client.py          # Ollama client
│   │   ├── prompts.py               # System prompts & templates
│   │   └── response_parser.py       # Response parsing & formatting
│   │
│   ├── embeddings/                  # Text Processing
│   │   ├── embedding_model.py       # BGE embeddings
│   │   └── chunking.py              # Text chunking with overlap
│   │
│   ├── vectordb/                    # Vector Database
│   │   ├── chroma_client.py         # ChromaDB initialization
│   │   ├── api_vector_store.py      # API tool indexing
│   │   └── retriever.py             # Semantic search & retrieval
│   │
│   ├── cache/                       # Caching Layer
│   │   └── redis_cache.py           # Redis cache implementation
│   │
│   ├── services/                    # External Services
│   │   ├── hrms_api_client.py       # HRMS API HTTP client
│   │   └── (Other API clients)
│   │
│   ├── tools/                       # Tool Definitions
│   │   └── api_registry.json        # OpenAPI registry for HRMS APIs
│   │
│   ├── config.py                    # Configuration & env variables
│   └── main.py                      # FastAPI app initialization
│
├── docker/
│   ├── Dockerfile                   # Container image definition
│   ├── docker-compose.yml           # Multi-container orchestration
│   ├── .env.example                 # Environment template
│   └── README.md                    # Docker setup guide
│
├── scripts/
│   ├── build_registry.py            # Fetch & build API registry from Swagger
│   └── index_api_registry.py        # Index APIs into vector database
│
├── chroma_db/                       # Vector database storage (local)
├── dump.rdb                         # Redis snapshot (local)
│
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
└── .env.example                     # Environment template

```

---

## Prerequisites

### System Requirements
- Docker Desktop installed (https://www.docker.com/products/docker-desktop/)
- At least 4GB RAM available
- Internet connection (for downloading images)

### External Services
1. **Ollama Server** - LLM inference
   - Runs in Docker container automatically
   - Default URL: `http://ollama:11434`
   
2. **Redis** - Caching
   - Runs in Docker or local server
   - Default: `localhost:6379`
   
3. **HRMS API** - Your HR management system
   - Must be accessible from container
   - Requires API token/credentials

---

## Installation & Setup

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd hrms_ai_service
```

### 2. Create Environment File

Choose Option A (recommended for sharing) or Option B (local development):

**Option A: Docker Deployment (Using Pre-built Image)**

```bash
cd docker
cp .env.example .env
# Edit .env with your configuration
docker compose up
```

**Option B: Local Development (Build from Source)**

```bash
cd docker
cp .env.example .env
# Edit .env with your configuration
docker compose up --build
```

### 3. Configure Environment Variables

Edit `docker/.env`:

```env
# ======================
# Ollama Configuration
# ======================
OLLAMA_URL=http://ollama:11434
LLM_MODEL=llama3
EMBED_MODEL=BAAI/bge-small-en
CHROMA_PATH=/app/chroma_db

# ======================
# HRMS API Configuration
# ======================
HRMS_API_BASE_URL=https://hrmsapi.leanxpert.in
HRMS_API_TOKEN=your_actual_token_here

# ======================
# Redis Configuration
# ======================
REDIS_URL=redis://localhost:6379
CACHE_TTL=600

# ======================
# Application Configuration
# ======================
APP_PORT=8000
```

### 4. Start Services

```bash
cd docker
docker compose up
```

**Services started:**
- FastAPI server: http://localhost:8000
- Ollama LLM: http://localhost:11434
- Redis cache: localhost:6379
- ChromaDB: embedded in app

### 5. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"ok"}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://ollama:11434` | URL to Ollama LLM service |
| `LLM_MODEL` | `llama3` | Model to use (llama3, mistral, etc.) |
| `EMBED_MODEL` | `BAAI/bge-small-en` | Embedding model for text chunks |
| `CHROMA_PATH` | `/app/chroma_db` | Path to vector database |
| `HRMS_API_BASE_URL` | — | Your HRMS API endpoint |
| `HRMS_API_TOKEN` | — | HRMS API authentication token |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `CACHE_TTL` | `600` | Cache expiration time (seconds) |
| `APP_PORT` | `8000` | FastAPI server port |

### Port Conflicts

If port 8000 is already in use:

```bash
# Edit docker/.env
APP_PORT=9000

# Restart
docker compose down
docker compose up
```

---

## API Documentation

### Interactive API Docs

**Swagger UI:** http://localhost:8000/docs  
**ReDoc:** http://localhost:8000/redoc

### Endpoints

#### 1. Chat Endpoint

**POST** `/chat`

Process a natural language query and get an AI-generated response.

**Request Body:**
```json
{
  "question": "Show employee 102"
}
```

**Response:**
```json
{
  "answer": "Employee ID 102, John Doe, works in IT Department with salary $85,000. Employment status: Active"
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid request
- `500` - Internal server error

**Example using cURL:**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the leave policy?"}'
```

**Example using Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/chat",
    json={"question": "Show employee 102"}
)
print(response.json()["answer"])
```

#### 2. Health Check Endpoint

**GET** `/health`

Verify service is running.

**Response:**
```json
{
  "status": "ok"
}
```

**Status Codes:**
- `200` - Service is healthy

**Example:**
```bash
curl http://localhost:8000/health
```

---

## System Architecture

### High-Level Flow

```
User Query
    ↓
[Intent Classification]
    ├→ "policy" query (HR policies)
    │   ↓
    │ [Policy Service - RAG]
    │   ├→ Embed query
    │   ├→ Search ChromaDB
    │   ├→ Generate response
    │   ↓
    │ Response to user
    │
    └→ "data" query (Employee/HR data)
        ↓
      [Agent Router - Data Pipeline]
        ├→ Classify domain (employee, department, salary, etc.)
        ├→ Extract entities (IDs, names, departments)
        ├→ Plan tools (find best HRMS APIs using hybrid ranking)
        ├→ Validate tools
        ├→ Execute API calls
        ├→ Parse responses
        ├→ Generate natural language answer
        ↓
      Response to user
```

### Two Processing Pipelines

#### Pipeline 1: Policy Queries (RAG)
```
Input: "What is the leave policy?"
  ↓
Intent Classification → "policy"
  ↓
Policy Service
  ├→ Embed question using BAAI/bge-small-en
  ├→ Search ChromaDB for similar policy chunks
  ├→ Retrieve relevant policy documents
  ├→ Add context to LLM prompt
  ↓
LLM Response Generation (via Ollama)
  ↓
Output: "The leave policy states... [full policy details]"
```

#### Pipeline 2: Data Queries (APIs)
```
Input: "Show employee 102"
  ↓
Intent Classification → "data"
  ↓
Agent Router (7-step pipeline)
  ├ Step 1: Domain Classification → "employee"
  ├ Step 2: Entity Extraction → ["102"] (employee ID)
  ├ Step 3: Tool Planning (hybrid ranking)
  │         ├→ Semantic search: embeddings vs API schemas
  │         ├→ Keyword matching: BM25
  │         ├→ Combined ranking
  │         └→ Select top API: "GET /employees/{id}"
  ├ Step 4: Tool Validation
  ├ Step 5: API Execution → GET /employees/102
  ├ Step 6: Response Parsing → Extract JSON fields
  │         └→ employee_id, name, department, salary, etc.
  ├ Step 7: LLM Answer Generation
  │         └→ Format as: "Employee ID 102, John Doe, IT Department..."
  ↓
Output: Formatted natural language response
```

### Component Interaction Diagram

```
┌─────────────────────────────────────────────────────┐
│                 FastAPI Application                 │
│  ┌──────────────────────────────────────────────┐   │
│  │  POST /chat (ChatRequest → ChatResponse)     │   │
│  └──────────────────┬───────────────────────────┘   │
│                     ↓                                 │
│  ┌─────────────────────────────────────────────┐   │
│  │  RAG Engine (answer_question)                │   │
│  │  ├→ Step 1: Cache Check (Redis)              │   │
│  │  ├→ Step 2: Build Context (prev messages)    │   │
│  │  ├→ Step 3: Route Query (Intent)             │   │
│  │  ├→ Step 4a: Policy Path → RAG Pipeline      │   │
│  │  │           └→ Policy Service + ChromaDB    │   │
│  │  ├→ Step 4b: Data Path → Agent Router        │   │
│  │  │           ├→ Domain Classifier            │   │
│  │  │           ├→ Tool Planner + Executor     │   │
│  │  │           ├→ HRMS API Client             │   │
│  │  │           └→ Response Parser             │   │
│  │  ├→ Step 5: LLM Generation (Ollama)          │   │
│  │  ├→ Step 6: Cache Result (Redis)             │   │
│  │  └→ Step 7: Return Response                  │   │
│  └─────────────────────────────────────────────┘   │
│                     ↓                                 │
│  ┌─────────┬─────────┬──────────┬──────────────┐   │
│  ↓         ↓         ↓          ↓              ↓    │
│ Ollama  ChromaDB  Redis    HRMS API      Embeddings │
│ (LLM)   (Vector)  (Cache)   (External)  (BAAI/bge) │
└─────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. RAG Engine (app/core/rag_engine.py)

**Purpose:** Main orchestration engine that coordinates all pipelines

**Main Function:**
```python
def answer_question(question: str, session_id: str = "default") -> str
```

**8-Step Process:**
1. Check Redis cache
2. Build conversation context from history
3. Route query (policy vs data)
4. Execute appropriate pipeline
5. Generate LLM response
6. Cache result
7. Store in conversation context
8. Return formatted answer

**Key Variables:**
- `cache_key`: Unique key for caching queries
- `conversation_context`: Previous messages for context
- `route_type`: "policy" or "data"
- `final_answer`: LLM-generated response

### 2. Intent Classifier (app/core/intent_classifier.py)

**Purpose:** Classify user intent into one of 10 categories

**Main Function:**
```python
def classify_intent(question: str) -> str
    # Returns: "policy" | "data"
```

**Supported Intents:**
- Policy queries: leave, benefits, compensation, compliance
- Data queries: employee, department, salary, attendance

**Implementation:**
- Uses Ollama LLM
- Prompt-based classification
- Cached for performance

### 3. Tool Planner (app/core/tool_planner.py)

**Purpose:** Rank and select best HRMS APIs for a given query

**Main Function:**
```python
def find_tool(domain: str, question: str, entities: dict) -> dict
    # Returns: {"api": "/employees/{id}", "method": "GET", "params": {...}}
```

**8-Stage Hybrid Ranking Algorithm:**

1. **Load API Registry** - Read api_registry.json
2. **Semantic Search** - Embed question & API descriptions using BAAI/bge-small-en
3. **Similarity Scoring** - Calculate cosine similarity
4. **Keyword Matching** - BM25 ranking on API descriptions
5. **Domain Filtering** - Filter APIs by domain
6. **Entity Matching** - Match extracted entities to API parameters
7. **Score Combination** - Weighted average: 60% semantic + 40% BM25
8. **Select Top API** - Return highest-scoring candidate

**Example:**
```
Input: question="Show employee 102", domain="employee", entities={"id": 102}
↓
Semantic search on embeddings
Keyword matching on API docs
Combined ranking
↓
Output: {
  "api": "/employees/{id}",
  "method": "GET",
  "params": {"id": 102},
  "description": "Get employee details by ID"
}
```

### 4. Policy Service (app/core/policy_service.py)

**Purpose:** Retrieve relevant HR policy documents using RAG

**Main Function:**
```python
def get_policy_context(question: str) -> str
    # Returns: Relevant policy text from ChromaDB
```

**RAG Pipeline:**
1. Fetch policies from API (or cache)
2. Chunk policy documents (500 tokens, 50 token overlap)
3. Generate embeddings using BAAI/bge-small-en
4. Store in ChromaDB vector database
5. For queries: embed question, semantic search in ChromaDB
6. Return top-k (default: 3) matching chunks

**Storage:**
- Policies stored in ChromaDB collections
- Collection name: "hrms_policies"
- Each document indexed with metadata

### 5. Agent Router (app/core/agent_router.py)

**Purpose:** Execute complete data query pipeline

**Main Function:**
```python
def route_query(question: str, context: str, entities: dict) -> str
    # Returns: Answer to the data query
```

**7-Step Pipeline:**
1. Domain classification (employee, department, salary, etc.)
2. Entity extraction (IDs, names, departments)
3. Tool planning (select best API via hybrid ranking)
4. Tool validation
5. API execution (actual HTTP call to HRMS)
6. Response parsing (extract relevant fields)
7. Answer generation (LLM formats as natural language)

### 6. LLM Integration (app/llm/llama_client.py)

**Purpose:** Interface with Ollama for LLM inference

**Main Function:**
```python
def generate_response(prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str
```

**Parameters:**
- `prompt`: User query + context + instructions
- `system_prompt`: System-level instructions
- `temperature`: 0.7 (for balanced creativity/consistency)
- `top_p`: 0.9 (nucleus sampling)
- `num_ctx`: 2048 (context window)

**Used For:**
- Intent classification
- Domain classification
- Entity extraction
- Final answer generation

### 7. Vector Database (app/vectordb/)

**ChromaDB Implementation:**
```python
class ChromaDB:
    - get_chroma_client() → chroma.Client
    - get_hrms_collection() → Collection for policies
    - add_documents(docs, embeddings) → store
    - query(embedding, top_k=3) → retrieve similar docs
```

**Collections:**
- `hrms_policies`: Policy documents and procedures
- `api_schemas`: API documentation indexed for tool discovery

### 8. Redis Cache (app/cache/redis_cache.py)

**Purpose:** Caching layer for repeated queries

**Configuration:**
- **TTL:** 600 seconds (10 minutes)
- **Key Format:** `"rag:{question}"` for query cache
- **Operations:** get, set, delete

**Cache Keys:**
- Query results: `rag:{question}`
- Intent classifications: `intent:{question}`
- Tool selections: `tool:{domain}:{question}`

---

## Processing Pipeline

### Request → Response Flow

```
POST /chat
{
  "question": "Show employee 102"
}
    ↓
[app/api/routes/chat.py]
chat(ChatRequest) → answer_question(question)
    ↓
[app/core/rag_engine.py]
answer_question() - 8 steps:
    ↓
Step 1: Check cache
    - Key: rag:{question}
    - If hit: return cached answer (SKIP to step 7)
    - If miss: continue
    ↓
Step 2: Build context
    - Load conversation history from session
    - Format previous exchanges
    ↓
Step 3: Route query
    - Call intent_classifier.classify_intent()
    - Determine: "policy" or "data"
    ↓
Step 4a-b: Execute pipeline
    
    IF policy query:
    - Call policy_service.get_policy_context()
    - Retrieve documents from ChromaDB
    - Use as context for LLM
    
    IF data query:
    - Call agent_router.route_query()
    - Execute 7-step data pipeline (see below)
    
    ↓
Step 5: Generate LLM response
    - Call llama_client.generate_response()
    - Ollama inference with context
    ↓
Step 6: Cache result
    - Store in Redis with TTL=600s
    ↓
Step 7: Return response

{
  "answer": "Employee ID 102, John Doe, IT Department..."
}
```

### Agent Router (Data Query) - Detailed 7 Steps

```
Input: question="Show employee 102"

Step 1: Domain Classification
    ├→ LLM call: "What domain is this? employee/department/salary/etc"
    ├→ Output: "employee"
    ↓

Step 2: Entity Extraction
    ├→ LLM call: "Extract IDs, names, values from: [question]"
    ├→ Output: entities = {"employee_id": "102"}
    ↓

Step 3: Tool Planning (Hybrid Ranking)
    ├→ Load api_registry.json APIs
    ├→ Semantic search: embed question vs API descriptions
    ├→ BM25 keyword matching
    ├→ Combined scoring: 60% semantic + 40% keyword
    ├→ Filter by domain: keep only "employee" APIs
    ├→ Match entities to API params
    ├→ Output: selected_api = {
    │     "api": "/employees/{id}",
    │     "method": "GET",
    │     "params": {"id": "102"}
    │   }
    ↓

Step 4: Tool Validation
    ├→ Verify API exists in registry
    ├→ Check params match function signature
    ├→ Validate param types
    ├→ Output: validation_passed = true
    ↓

Step 5: API Execution
    ├→ Call hrms_api_client.execute_api()
    ├→ GET http://hrmsapi.leanxpert.in/employees/102
    ├→ Response (JSON):
    │   {
    │     "id": 102,
    │     "name": "John Doe",
    │     "department": "IT",
    │     "designation": "Senior Developer",
    │     "salary": 85000,
    │     "status": "Active"
    │   }
    ↓

Step 6: Response Parsing
    ├→ Extract relevant fields from JSON
    ├→ Format for LLM consumption
    ├→ Output: parsed_data = {
    │     "employee_id": 102,
    │     "name": "John Doe",
    │     "department": "IT",
    │     "designation": "Senior Developer",
    │     "salary": 85000,
    │     "status": "Active"
    │   }
    ↓

Step 7: Answer Generation
    ├→ LLM call with parsed data
    ├→ Prompt: "Format this data as a natural response..."
    ├→ Output: "Employee ID 102, John Doe, works in the IT Department as a Senior Developer with a salary of $85,000. Current status: Active"

Final Answer returned to user
```

---

## Example Queries

### Example 1: Data Query - Show Employee

**Request:**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "Show employee 102"}'
```

**Processing:**
```
Intent: "data" (requires API call)
Domain: "employee"
Entities: {"employee_id": 102}
Selected API: GET /employees/{id}
API Response: {id: 102, name: "John Doe", dept: "IT", salary: 85000}
LLM Generation: "Format this as a natural response"
```

**Response:**
```json
{
  "answer": "Employee ID 102, John Doe, is a Senior Developer in the IT Department with a salary of $85,000. Employment status: Active."
}
```

---

### Example 2: Policy Query - Leave Policy

**Request:**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the leave policy?"}'
```

**Processing:**
```
Intent: "policy" (requires RAG)
Embed question: [0.12, 0.45, 0.78, ...] (384-dim vector)
Search ChromaDB: Find 3 most similar policy chunks
Retrieved: "Leave policy states: Employees get 20 days PTO..."
LLM Generation: Generate comprehensive response using policy context
```

**Response:**
```json
{
  "answer": "According to the leave policy, employees are entitled to 20 days of Paid Time Off (PTO) per year. For maternity leave, eligible employees receive 12 weeks of paid leave. Sick leave is 10 days per year. All leave requests must be submitted 2 weeks in advance through the HR portal."
}
```

---

### Example 3: Multi-Step Query

**Request:**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "List employees in IT department"}'
```

**Processing:**
```
Intent: "data"
Domain: "department"
Entities: {"department": "IT"}
Selected API: GET /departments/IT/employees
API Response: [
  {id: 102, name: "John", role: "Developer"},
  {id: 103, name: "Jane", role: "Manager"},
  {id: 105, name: "Bob", role: "QA"}
]
LLM Formatting: Convert list to natural language
```

**Response:**
```json
{
  "answer": "The IT Department has 3 employees: John (Developer), Jane (Manager), and Bob (QA Specialist)."
}
```

---

## Troubleshooting

### Issue: Connection to Ollama Failed

**Error:** `Connection refused: http://ollama:11434`

**Solutions:**
1. Check Ollama is running: `docker logs <ollama-container>`
2. Wait 30 seconds for Ollama to start
3. Verify network: `docker network ls`
4. Rebuild: `docker compose down && docker compose up --build`

### Issue: ChromaDB Collection Not Found

**Error:** `Collection 'hrms_policies' not found`

**Solution:**
Run the indexing script:
```bash
python scripts/index_api_registry.py
```

### Issue: Port 8000 Already in Use

**Solution:**
Change port in `docker/.env`:
```
APP_PORT=9000
```
Then restart: `docker compose down && docker compose up`

### Issue: Redis Connection Failed

**Error:** `Connection refused: localhost:6379`

**Solutions:**
1. Check Redis is running: `docker ps | grep redis`
2. Clear cache flag in code (fallback to no-cache mode)
3. Restart Redis: `docker compose restart redis`

### Issue: HRMS API Call Fails

**Error:** `401 Unauthorized` or `Connection failed`

**Solutions:**
1. Verify `HRMS_API_BASE_URL` in `.env`
2. Check `HRMS_API_TOKEN` is correct
3. Test API manually: `curl http://api-url/health`
4. Check network connectivity: `docker exec hrms-ai-service ping hrmsapi.leanxpert.in`

### Issue: Slow Response Times

**Cause:** Ollama model is slow or LLM context is large

**Solutions:**
1. Use smaller model: `LLM_MODEL=mistral-lite`
2. Reduce context window in llama_client.py
3. Increase cache TTL: `CACHE_TTL=3600` (1 hour)
4. Check server resources: `docker stats`

---

## Development

### Running Locally (Without Docker)

**Prerequisites:**
```bash
# Install Python 3.11
# Install system dependencies
pip install -r requirements.txt

# Start services separately
ollama serve
redis-server
```

**Run application:**
```bash
python -m uvicorn app.main:app --reload
```

### Building & Deploying Docker Image

**Build locally:**
```bash
docker build -f docker/Dockerfile -t myregistry/hrms_ai:latest .
```

**Push to Docker Hub:**
```bash
docker login
docker push myregistry/hrms_ai:latest
```

**Run from image:**
```bash
docker run -p 8000:8000 --env-file .env myregistry/hrms_ai:latest
```

### Adding New HRMS APIs

1. Add Swagger URL to `scripts/build_registry.py`
2. Run: `python scripts/build_registry.py`
3. Index into vector DB: `python scripts/index_api_registry.py`
4. System will automatically discover and rank new APIs

### Testing

**Manual API testing:**
```python
import requests
response = requests.post(
    "http://localhost:8000/chat",
    json={"question": "Show employee 102"}
)
print(response.json())
```

**Debug logging:**
Add to any file:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug(f"Variable: {variable}")
```

---

## Support & Resources

- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Ollama Project:** https://ollama.ai
- **ChromaDB Docs:** https://docs.trychroma.com
- **Docker Docs:** https://docs.docker.com

---

**Last Updated:** March 2026  
**Version:** 1.0.0  
**Maintainer:** Shyam Manohar

• keyword matching
• semantic similarity

Tool Executor
Calls HRMS API.

RAG Engine
Retrieves HR policies from vector store.

LLM Client
Uses Ollama for reasoning.

---

# Deployment

The system is fully containerized using Docker.

Run with:

```
docker compose up --build
```

---
