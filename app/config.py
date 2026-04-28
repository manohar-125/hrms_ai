from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):

    LLM_PROVIDER: str = "openai"
    EMBED_MODEL: str
    CHROMA_PATH: str

    OPENAI_MODEL: str = "gpt-4o-mini"
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
    GEMINI_MODEL: str = "gemini-2.0-flash"

    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    HRMS_API_BASE_URL: str
    HRMS_API_TOKEN: str
    
    # Redis configuration (optional with defaults)
    ENABLE_CACHE: bool = True
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