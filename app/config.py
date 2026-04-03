from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):

    OLLAMA_URL: str
    LLM_MODEL: str
    EMBED_MODEL: str
    CHROMA_PATH: str

    HRMS_API_BASE_URL: str
    HRMS_API_TOKEN: str
    
    # Redis configuration (optional with defaults)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # API Selection configuration (tunable for accuracy)
    SEMANTIC_SEARCH_K: int = 10  # Number of candidates from semantic search
    KEYWORD_WEIGHT: float = 0.5  # Weight for keyword score in hybrid scoring (0.0 to 1.0)
    SIMILARITY_THRESHOLD: float = 0.2  # Minimum similarity score to consider an API
    REQUIRE_HIGH_CONFIDENCE: bool = True  # Require high similarity (>0.5) to auto-select

    class Config:
        # Look for .env in project root (2 levels up from app/)
        env_file = str(Path(__file__).parent.parent / ".env")

settings = Settings()