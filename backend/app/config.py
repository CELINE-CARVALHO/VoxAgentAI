"""
Centralized app configuration, loaded from environment variables / .env file.
Every other module should import `settings` from here rather than reading
os.environ directly, so config stays in one place.
"""
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str = "sqlite:///./voxagent.db"

    # --- Auth ---
    JWT_SECRET: str = "change-this-to-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # # --- Gemini LLM ---
    # # GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    # GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5500,http://127.0.0.1:5500"

    # --- App ---
    APP_NAME: str = "VoxAgent AI Backend"
    ENV: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()