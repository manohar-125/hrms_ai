# HRMS AI Service

AI-powered backend that enables **natural language interaction with an HRMS system**.

Instead of navigating complex HRMS interfaces, users can ask questions like:

* "Show employee 102"
* "List departments"
* "Show employee bank account details"
* "What is the leave policy?"

The system automatically determines whether to:

• Call HRMS APIs
• Retrieve policy documents using RAG
• Use an LLM for reasoning

---

# Architecture

User Query
↓
Intent Classifier
↓
Domain Classifier
↓
Tool Planner
↓
HRMS API / RAG / LLM
↓
Formatted Response

---

# Tech Stack

Backend

* FastAPI
* Python

AI Components

* Ollama (LLM inference)
* ChromaDB (vector database)
* BAAI/bge-small-en (embeddings)

Infrastructure

* Docker
* Docker Compose

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
│   │
│   ├── core
│   │   ├── intent_classifier.py
│   │   ├── domain_classifier.py
│   │   ├── agent_router.py
│   │   ├── tool_planner.py
│   │   ├── tool_executor.py
│   │   └── rag_engine.py
│   │
│   ├── embeddings
│   ├── llm
│   ├── services
│   ├── vectordb
│   │
│   ├── config.py
│   └── main.py
│
├── docker
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── scripts
├── requirements.txt
├── README.md
└── .env.example
```

---

# Features

• Natural language HRMS queries
• Automatic tool selection using hybrid ranking
• RAG pipeline for HR policies
• Vector search with ChromaDB
• LLM reasoning using Ollama
• Dockerized deployment

---

# Running the Project

## Prerequisites

Install Docker Desktop

https://www.docker.com/products/docker-desktop/

---

## Clone Repository

```
git clone https://github.com/<your-username>/hrms-ai-service.git
cd hrms-ai-service
```

---

## Create Environment File

```
cp .env.example .env
```

Example `.env`:

```
OLLAMA_URL=http://ollama:11434
LLM_MODEL=llama3
EMBED_MODEL=BAAI/bge-small-en
CHROMA_PATH=/app/chroma_db

HRMS_API_BASE_URL=https://hrmsapi.leanxpert.in
HRMS_API_TOKEN=dummy_token
```

---

## Start Services

```
cd docker
docker compose up --build
```

This will start:

• FastAPI server
• Ollama LLM
• Vector DB

---

## Open API Documentation

```
http://localhost:8000/docs
```

---

# Example Queries

POST `/chat`

Example:

```
{
  "query": "Show employee 102"
}
```

Other queries:

• "List departments"
• "Show employee bank account details"
• "Show employee employment details"

---

# Components

Intent Classifier
Determines the user intent.

Domain Classifier
Identifies HR domain (employee, department, salary).

Tool Planner
Ranks available APIs using:

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
