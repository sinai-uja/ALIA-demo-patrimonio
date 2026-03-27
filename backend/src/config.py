from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="config/.env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "postgresql+asyncpg://uja:uja@localhost:5432/uja_iaph"

    # Embedding service
    embedding_service_url: str = "http://localhost:8001"
    embedding_api_key: str = ""
    embedding_dim: int = 768

    # LLM service
    llm_provider: str = "gemini"  # "vllm" or "gemini"
    llm_service_url: str = "http://localhost:8000/v1"
    llm_api_key: str = ""
    llm_model_name: str = "BSC-LT/salamandra-7b-instruct"
    llm_max_tokens: int = 512
    llm_route_narrative_max_tokens: int = 2048
    llm_temperature: float = 0.3

    # Gemini
    gemini_api_key: str = ""
    gemini_model_name: str = "gemini-3.1-flash-lite-preview"

    # Embedding query instruction (Qwen3 instruction-aware prefix)
    # Set to empty string to disable (e.g. for MrBERT)
    embedding_query_instruction: str = "Retrieve relevant heritage documents."

    # RAG
    rag_similarity_only: bool = False
    rag_similarity_threshold: float = 0.45
    rag_top_k: int = 5
    rag_retrieval_k: int = 20
    search_retrieval_k: int = 200
    search_score_threshold: float = 0.55
    rag_score_threshold: float = 0.50
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64
    chunks_table_version: str = "v1"

    @property
    def chunks_table_name(self) -> str:
        return f"document_chunks_{self.chunks_table_version}"

    # API
    api_v1_prefix: str = "/api/v1"
    project_name: str = "IAPH Heritage RAG"
    debug: bool = False

    # CORS
    cors_origins: str = "*"

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("+asyncpg", "")

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
