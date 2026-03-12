from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="config/.env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://uja:uja@localhost:5432/uja_iaph"

    # Embedding service
    embedding_service_url: str = "http://localhost:8001"
    embedding_dim: int = 768

    # LLM service
    llm_service_url: str = "http://localhost:8000/v1"
    llm_model_name: str = "BSC-LT/salamandra-7b-instruct"
    llm_max_tokens: int = 512
    llm_temperature: float = 0.7

    # RAG
    rag_top_k: int = 5
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64

    # API
    api_v1_prefix: str = "/api/v1"
    project_name: str = "IAPH Heritage RAG"
    debug: bool = False


settings = Settings()
