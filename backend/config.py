"""
config.py — Central configuration for MoneyLogix Strategy Builder.
All values can be overridden via environment variables or .env file.
"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # AI Provider: "mock", "huggingface", or "claude"
    AI_PROVIDER: str = "mock"
    
    # API Keys
    ANTHROPIC_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""


#if hf account and api is there use this and comment out from line 10-14, and uncomment the below 3 lines and add api below
    # AI_PROVIDER: str = "huggingface"
    # HUGGINGFACE_API_KEY: str = "add your huggingface api key here"
    # ANTHROPIC_API_KEY: str = ""

    # Data layer
    NSE_TIMEOUT_SECONDS: int = 3
    CACHE_TTL_SECONDS: int = 60

    # Health monitoring
    HEALTH_MONITOR_INTERVAL_SECONDS: int = 60

    # Options math
    RISK_FREE_RATE: float = 0.065  # India 10-year government bond rate

    # Database
    DATABASE_URL: str = "sqlite:///./moneylogix.db"

    # Server
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]  # Vite default port

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()