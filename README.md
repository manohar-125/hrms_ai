Below is a **complete professional README.md** you can directly place in your repository.
It is written like **real production documentation** so it is useful for:

* GitHub portfolio
* Team handover
* Supervisor review
* Interviews
* Open-source projects

---

# HRMS AI Service

AI-powered backend that enables **natural language interaction with an HRMS system**.

Instead of navigating complex HRMS interfaces, users can ask questions like:

```
Show departments
Show employee 102
List projects
Show clients
What is leave policy?
```

The system automatically:

1. Understands the user query
2. Decides whether the query requires **HRMS API data or HR policy knowledge**
3. Selects the correct **HRMS API**
4. Executes the API
5. Converts the response into a **human-readable answer using an LLM**

The system functions as an **AI Copilot for the HRMS platform**.

---

# Architecture Overview

The system uses a **Hybrid AI Agent + RAG Architecture**.

```
User Query
     │
     ▼
FastAPI /chat endpoint
     │
     ▼
RAG Engine
     │
     ▼
Query Router
     │
     ├── Policy Query → RAG Pipeline
     │                     │
     │                     ▼
     │               Vector DB (Chroma)
     │                     │
     │                     ▼
     │                  LLM Answer
     │
     └── Data Query → Tool Agent
                        │
                        ▼
                   Domain Classifier
                        │
                        ▼
                   Semantic Tool Search
                        │
                        ▼
                   Tool Planner (LLM)
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
                   Response Parser
                        │
                        ▼
                     LLM Answer
```

---

# Key Features

### Natural Language HRMS Queries

Users can query HRMS data using plain English.

Examples:

```
show departments
show employee 102
list projects
show clients
show attendance
```

---

### AI Tool Agent System

The AI system automatically selects the correct HRMS API.

Example:

```
Query: show departments
Tool Selected: GET /api/Department
```

---

### Semantic API Search

Instead of sending **300+ APIs to the LLM**, the system performs:

```
Query → Vector Search → Top 5 APIs → LLM selection
```

This significantly improves tool accuracy.

---

### Retrieval Augmented Generation (RAG)

Policy queries are answered using vector search over policy documents.

Example queries:

```
what is leave policy
explain attendance policy
```

---

### Dynamic HRMS API Execution

The system dynamically calls HRMS APIs such as:

```
/api/Department
/api/Project
/api/Client
/api/EmpReg
/api/LeavePolicy
/api/Salary
/api/Task
```

---

### Automatic API Registry

The tool registry can be generated automatically from Swagger.

Script:

```
scripts/build_registry.py
```

---

### Redis Caching

Frequently repeated queries are cached.

Example:

```
show departments
show projects
```

Flow:

```
Query
 ↓
Redis Cache
 ├ hit → return cached response
 └ miss → run pipeline
```

---

# Technology Stack

| Layer                | Technology                  |
| -------------------- | --------------------------- |
| Backend API          | FastAPI                     |
| Programming Language | Python                      |
| LLM                  | Llama3 (Ollama)             |
| Vector Database      | ChromaDB                    |
| Embeddings           | BGE (BAAI/bge-small-en)     |
| Caching              | Redis                       |
| API Communication    | Python requests             |
| Architecture         | AI Agent + Tool Layer + RAG |

---

# Project Structure

```
hrms_ai_service
│
├── app
│   ├── api
│   │   ├── routes
│   │   │   ├── admin.py
│   │   │   ├── chat.py
│   │   │   └── health.py
│   │   └── schemas
│   │       ├── chat_schema.py
│   │       └── response_schema.py
│
│   ├── core
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
│
│   ├── embeddings
│   │   ├── chunking.py
│   │   └── embedding_model.py
│
│   ├── llm
│   │   ├── llama_client.py
│   │   ├── prompts.py
│   │   └── response_parser.py
│
│   ├── services
│   │   ├── auth_service.py
│   │   ├── hrms_api_client.py
│   │   └── swagger_client.py
│
│   ├── tools
│   │   └── api_registry.json
│
│   ├── vectordb
│   │   ├── api_vector_store.py
│   │   ├── chroma_client.py
│   │   ├── retriever.py
│   │   └── vector_store.py
│
│   ├── config.py
│   ├── dependencies.py
│   └── main.py
│
├── docker
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── scripts
│   ├── build_registry.py
│   └── index_api_registry.py
│
├── requirements.txt
└── README.md
```

---

# Core Components

## FastAPI Backend

Entry point:

```
app/main.py
```

Main endpoint:

```
POST /chat
```

Example request:

```json
{
 "question": "show departments"
}
```

---

## RAG Engine

File:

```
core/rag_engine.py
```

Responsible for:

* routing queries
* executing tool agent pipeline
* executing policy RAG pipeline

---

## Domain Classifier

File:

```
core/domain_classifier.py
```

Classifies queries into domains such as:

```
employee
department
attendance
leave
project
task
client
policy
general
```

---

## Tool Planner

File:

```
core/tool_planner.py
```

Responsible for selecting the best API tool.

Process:

```
1. Detect domain
2. Semantic API search
3. LLM selects best tool
```

---

## Tool Executor

File:

```
core/tool_executor.py
```

Executes the selected HRMS API.

Example:

```
GET https://hrmsapi.leanxpert.in/api/Department
```

---

## Tool Validator

File:

```
core/tool_validator.py
```

Ensures:

* tool exists
* endpoint exists
* parameters are valid

---

## Policy RAG System

File:

```
core/policy_service.py
```

Used for HR policy queries.

Flow:

```
Query
 ↓
Vector DB search
 ↓
Retrieve policy chunks
 ↓
LLM generates answer
```

---

# Vector Database

Vector store:

```
ChromaDB
```

Location:

```
chroma_db/
```

Stores:

* HR policy embeddings
* API embeddings

---

# API Tool Registry

File:

```
app/tools/api_registry.json
```

Example:

```
{
 "get_department": {
   "domain": "department",
   "endpoint": "/api/Department",
   "method": "GET",
   "description": "Fetch all departments"
 }
}
```

---

# Running the Project

## 1. Install Dependencies

```
pip install -r requirements.txt
```

---

## 2. Start Ollama

```
ollama serve
```

Run model:

```
ollama run llama3
```

---

## 3. Start Redis (optional)

```
redis-server
```

---

## 4. Run the API Server

```
uvicorn app.main:app --reload
```

---

## 5. Open API Docs

```
http://localhost:8000/docs
```

---

# Example Queries

```
show departments
show projects
list clients
show employees
show employee 102
show cities
show banks
what is leave policy
```

---

# Future Improvements

Planned enhancements:

* improved entity extraction
* parameter detection
* conversation memory
* async API execution
* tool confidence scoring
* fallback tool strategies
* advanced caching strategies

---

# Final Goal

The goal of this project is to create a **fully autonomous AI Copilot for HRMS systems** that allows employees and administrators to retrieve HRMS data through natural language queries while automatically executing the correct APIs and retrieving relevant policy information.

---
