"""config.py — Central configuration for MoneyLogix Strategy Builder."""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    AI_PROVIDER: str = "mock"
    ANTHROPIC_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""

    NSE_TIMEOUT_SECONDS: int = 3
    CACHE_TTL_SECONDS: int = 60
    HEALTH_MONITOR_INTERVAL_SECONDS: int = 60

    RISK_FREE_RATE: float = 0.065
    DATABASE_URL: str = "sqlite:///./moneylogix.db"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()