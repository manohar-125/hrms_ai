# Docker Deployment Guide

Complete guide to deploy the HRMS AI Service using Docker on another system.

---

## ⚡ Quick Start (2-3 minutes)

```bash
# 1. Clone/copy project
git clone <your-repo> hrms_ai_service && cd hrms_ai_service

# 2. Setup environment
cp docker/.env.example .env
nano .env  # Edit with your HRMS API credentials and Ollama settings

# 3. Start all services
docker-compose -f docker/docker-compose.yml up --build -d

# 4. Wait for Ollama, then pull models (one-time)
docker exec -it hrms_ai_ollama ollama pull llama2
docker exec -it hrms_ai_ollama ollama pull nomic-embed-text

# 5. Verify deployment
curl http://localhost:8000/health
# Access API at: http://localhost:8000/docs
```

---

## Prerequisites

- Docker (version 20.10+)
- Docker Compose (version 2.0+)
- 4GB+ RAM available
- Internet connection (for pulling images)

## Full Setup Guide

### 1. Copy Project to New System

```bash
# Clone or copy entire project with docker/ folder
git clone <your-repo> hrms_ai_service
cd hrms_ai_service
```

### 2. Configure Environment Variables

```bash
# Copy example env file
cp docker/.env.example .env

# Edit with your configuration
nano .env
```

**Required variables to update:**
- `OLLAMA_URL`: Usually `http://ollama:11434` (when using Docker)
- `LLM_MODEL`: e.g., `llama2`, `mistral`, `neural-chat`
- `EMBED_MODEL`: e.g., `nomic-embed-text`, `all-minilm`
- `HRMS_API_BASE_URL`: Your HRMS system URL
- `HRMS_API_TOKEN`: Your HRMS API authentication token

### 3. Build and Start Services

```bash
# From project root
docker-compose -f docker/docker-compose.yml up --build -d
```

This will:
- Build HRMS AI Service image
- Start Redis (caching)
- Start Chroma (vector database)
- Start Ollama (LLM)
- Start the main API service

### 4. Pull Ollama Models (One-time Setup)

Wait 2-3 minutes for Ollama to start, then:

```bash
# Pull models
docker exec -it hrms_ai_ollama ollama pull llama2
docker exec -it hrms_ai_ollama ollama pull nomic-embed-text
```

Or use the Ollama API:
```bash
curl -X POST http://localhost:11434/api/pull -d '{"name": "llama2"}'
curl -X POST http://localhost:11434/api/pull -d '{"name": "nomic-embed-text"}'
```

### 5. Verify Deployment

```bash
# Check all containers running
docker-compose -f docker/docker-compose.yml ps

# Test API health
curl http://localhost:8000/health

# View logs
docker-compose -f docker/docker-compose.yml logs -f hrms-ai-service
```

## Service Details

| Service | Port | Purpose |
|---------|------|---------|
| hrms-ai-service | 8000 | Main FastAPI application |
| Ollama | 11434 | LLM inference engine |
| Redis | 6379 | Caching layer |
| Chroma | 8001 | Vector database |

## Accessing the API

| Endpoint | URL |
|----------|-----|
| Swagger Docs | `http://<your-server>:8000/docs` |
| ReDoc | `http://<your-server>:8000/redoc` |
| Health Check | `http://<your-server>:8000/health` |

## Common Operations

### Stop Services

```bash
# Stop but keep containers
docker-compose -f docker/docker-compose.yml stop

# Stop and remove containers
docker-compose -f docker/docker-compose.yml down

# Stop and remove all data (clean slate)
docker-compose -f docker/docker-compose.yml down -v
```

### View Logs

```bash
# All services
docker-compose -f docker/docker-compose.yml logs -f

# Specific service
docker-compose -f docker/docker-compose.yml logs -f hrms-ai-service

# Real-time stats
docker stats
```

### Manage Containers

```bash
# Restart a service
docker-compose -f docker/docker-compose.yml restart hrms-ai-service

# Execute command in container
docker exec -it hrms_ai_service bash

# Access Redis CLI
docker exec -it hrms_ai_redis redis-cli
```

## Troubleshooting

### Quick Fixes

| Issue | Solution |
|-------|----------|
| `port 8000 already in use` | Change port in docker-compose.yml or stop other service |
| `Ollama not responding` | Wait 2-3 minutes for startup, check: `curl http://localhost:11434` |
| `Models not found` | Pull them manually: `docker exec -it hrms_ai_ollama ollama pull llama2` |
| `Redis connection error` | Restart Redis: `docker-compose -f docker/docker-compose.yml restart redis` |

### Detailed Troubleshooting

**Service Won't Start**

```bash
# Check logs for errors
docker-compose -f docker/docker-compose.yml logs hrms-ai-service

# Rebuild containers
docker-compose -f docker/docker-compose.yml up --build -d
```

**Redis Connection Error**

```bash
# Check Redis is running and responsive
docker exec hrms_ai_redis redis-cli ping
# Should return: PONG
```

**Chroma Connection Error**

```bash
# Test Chroma endpoint
curl http://localhost:8001/api/v1
```

**Ollama Model Not Found**

```bash
# List available models
curl http://localhost:11434/api/tags

# Pull required model
docker exec -it hrms_ai_ollama ollama pull your-model-name
```

## Production Recommendations

1. **Use Named Volumes**: Already implemented for data persistence
2. **Health Checks**: Added for all services to auto-restart on failure
3. **Resource Limits**: Consider adding CPU/memory limits:

```yaml
services:
  hrms-ai-service:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

4. **Logging**: Configure Docker logging driver for centralized logs
5. **Backup**: Regularly backup `chroma_data` and `redis_data` volumes
6. **Reverse Proxy**: Use Nginx/Traefik in front for SSL/TLS

## Scaling and Optimization

### Multiple Instances

To run multiple API instances with load balancing:

```yaml
  hrms-ai-service:
    deploy:
      replicas: 3
    # Rest of config
```

### More Information

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Ollama Models](https://ollama.ai/library)
- [Chroma Documentation](https://docs.trychroma.com/)
