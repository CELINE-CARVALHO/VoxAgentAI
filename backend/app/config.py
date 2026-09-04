"""
Centralized application configuration.

All environment variables are loaded from the .env file.
Every module should import `settings` from here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ==========================================================
    # Database
    # ==========================================================
    DATABASE_URL: str = "sqlite:///./voxagent.db"

    # ==========================================================
    # Authentication
    # ==========================================================
    JWT_SECRET: str = "change-this-to-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # ==========================================================
    # Groq
    # ==========================================================
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ==========================================================
    # Knowledge Base
    # ==========================================================
    UPLOAD_FOLDER: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # ==========================================================
    # Pinecone (free tier — 1 serverless index, 100 K vectors)
    # ==========================================================
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "voxagent-knowledge"
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"

    # ==========================================================
    # Embedding Model (local, no API key needed)
    # ==========================================================
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ==========================================================
    # Logging
    # ==========================================================
    LOG_LEVEL: str = "INFO"

    # ==========================================================
    # CORS
    # ==========================================================
    CORS_ORIGINS: str = (
        "http://localhost:5500,"
        "http://127.0.0.1:5500,"
        "http://localhost:3000"
    )

    # ==========================================================
    # Application
    # ==========================================================
    APP_NAME: str = "VoxAgent AI Backend"
    ENV: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",        # Ignore any future .env variables
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()