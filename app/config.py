from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    OLLAMA_URL: str
    LLM_MODEL: str
    EMBED_MODEL: str
    CHROMA_PATH: str

    HRMS_API_BASE_URL: str
    HRMS_API_TOKEN: str

    class Config:
        env_file = ".env"


settings = Settings()