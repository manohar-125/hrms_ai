# HRMS AI Service

AI-powered backend service that enables **natural language interaction with an HRMS system**.
Users can ask questions like:

* “Show departments”
* “Who is employee 102?”
* “What is the leave policy?”
* “Show employee salary for March 2024”

The system automatically determines whether the query requires:

* **Policy retrieval (RAG)**
* **Live HRMS API execution**

This project implements a **Tool-Augmented AI Agent architecture** using FastAPI, LLMs, RAG, and dynamic API discovery.

---

# Architecture Overview

The system works as a hybrid **RAG + Tool Agent** architecture.

```
User Query
     │
     ▼
FastAPI /chat endpoint
     │
     ▼
Query Router
     │
     ├── Policy Query → RAG Engine
     │                   │
     │                   ▼
     │            ChromaDB Retrieval
     │                   │
     │                   ▼
     │                LLM Answer
     │
     └── Data Query → Tool Agent
                         │
                         ▼
                   Tool Planner
                         │
                         ▼
                   Tool Validator
                         │
                         ▼
                   Tool Executor
                         │
                         ▼
                     HRMS API
                         │
                         ▼
                      LLM Answer
```

---

# Key Features

### Natural Language HRMS Queries

Users interact with HRMS using plain English instead of APIs.

### Hybrid AI Architecture

The system automatically decides whether to use:

* **RAG for policy knowledge**
* **HRMS APIs for real-time data**

### Dynamic API Discovery

All HRMS APIs are automatically discovered from Swagger.

```
Swagger → Registry Generator → api_registry.json
```

Supports **300+ APIs automatically**.

### Tool-Based AI Agent

AI selects the correct API tool dynamically.

### Vector Database (RAG)

HR policies and documents are stored in **ChromaDB** and retrieved via semantic search.

### Redis Caching

Frequently asked questions are cached for faster responses.

### Modular Microservice Design

Clean architecture with independent modules for:

* routing
* tools
* LLM
* embeddings
* vector DB
* API services

---

# Project Structure

```
hrms_ai_service
│
├── app
│   ├── api                # FastAPI routes
│   │   ├── routes
│   │   └── schemas
│   │
│   ├── core               # Core AI logic
│   │   ├── rag_engine.py
│   │   ├── agent_router.py
│   │   ├── tool_planner.py
│   │   ├── tool_executor.py
│   │   ├── tool_validator.py
│   │   ├── query_router.py
│   │   ├── intent_classifier.py
│   │   ├── entity_extractor.py
│   │   └── domain_classifier.py
│   │
│   ├── embeddings         # Text embeddings
│   │   ├── chunking.py
│   │   └── embedding_model.py
│   │
│   ├── vectordb           # ChromaDB integration
│   │   ├── vector_store.py
│   │   ├── retriever.py
│   │   └── chroma_client.py
│   │
│   ├── llm                # LLM interaction layer
│   │   ├── llama_client.py
│   │   ├── prompts.py
│   │   └── response_parser.py
│   │
│   ├── services           # External services
│   │   ├── hrms_api_client.py
│   │   ├── swagger_client.py
│   │   └── auth_service.py
│   │
│   ├── tools              # API registry
│   │   └── api_registry.json
│   │
│   ├── config.py          # Environment configuration
│   ├── dependencies.py
│   └── main.py            # FastAPI entry point
│
├── chroma_db              # Vector database storage
├── docker                 # Docker setup
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── scripts
│   └── build_registry.py  # Swagger → API registry generator
│
├── requirements.txt
└── README.md
```

---

# How the AI Tool Agent Works

The tool agent allows the AI to execute HRMS APIs dynamically.

### Step 1 — Domain Detection

```
Query → Domain Classifier
Example:
"show departments" → department
```

### Step 2 — Tool Planning

The LLM selects the best API from the registry.

Example registry entry:

```
get_department
endpoint: /api/Department
method: GET
domain: department
```

### Step 3 — Tool Validation

Checks:

* endpoint exists
* parameters are valid
* request structure is correct

### Step 4 — API Execution

```
GET https://hrmsapi.leanxpert.in/api/Department
```

### Step 5 — Response Parsing

The API response is converted into a natural language answer.

---

# RAG Pipeline

Policy-related questions are answered using **Retrieval Augmented Generation**.

Example queries:

```
What is the leave policy?
Explain attendance policy
What is the work from home rule?
```

### RAG Flow

```
User Query
   │
   ▼
Embedding Generation
   │
   ▼
ChromaDB Retrieval
   │
   ▼
Context + Prompt
   │
   ▼
LLM Response
```

---

# API Endpoint

### Chat Endpoint

```
POST /chat
```

Example request:

```json
{
  "question": "show departments"
}
```

Example response:

```json
{
  "answer": "The organization currently has 5 departments..."
}
```

---

# Installation

### 1. Clone Repository

```
git clone https://github.com/your-repo/hrms_ai_service
cd hrms_ai_service
```

### 2. Create Virtual Environment

```
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```
pip install -r requirements.txt
```

### 4. Configure Environment

Update `app/config.py`

```
HRMS_API_BASE_URL=https://hrmsapi.leanxpert.in
HRMS_API_TOKEN=your_token_here
```

### 5. Start Server

```
uvicorn app.main:app --reload
```

Open Swagger:

```
http://localhost:8000/docs
```

---

# Generating API Registry

All HRMS APIs are automatically extracted from Swagger.

Run:

```
python scripts/build_registry.py
```

This generates:

```
app/tools/api_registry.json
```

---

# Example Queries

### HRMS Data Queries

```
show departments
show all employees
who is employee 102
show employee salary for March 2024
show project list
```

### HR Policy Queries

```
what is leave policy
explain attendance rules
what is work from home policy
```

---

# Known Limitations

Tool selection may sometimes call incorrect APIs when:

* multiple APIs have similar descriptions
* parameters are missing
* domain detection is ambiguous

Future improvements will include:

* semantic API search
* embedding-based tool retrieval
* improved entity extraction

---

# Future Improvements

Planned enhancements:

### Semantic API Search

Use embeddings to retrieve the most relevant APIs before LLM selection.

### Parameter Extraction

Automatically extract parameters such as:

```
employee id
project id
date ranges
```

### Improved Domain Classifier

More accurate routing between HR domains.

### Tool Memory

Cache successful tool calls for faster future responses.

### Observability

Add tracing, metrics, and monitoring.

---

# Technologies Used

* **FastAPI**
* **Python**
* **Ollama / Llama**
* **ChromaDB**
* **Redis**
* **Swagger / OpenAPI**
* **Docker**

---

# Authors

Developed as part of the **HRMS AI Service project** to enable intelligent interaction with enterprise HR systems using AI.

---

# License

Internal project – not licensed for external distribution.
