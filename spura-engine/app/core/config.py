from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://spura_user:spura_password@localhost:5432/spura_db"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "spura_db"
    DB_USER: str = "spura_user"
    DB_PASSWORD: str = "spura_password"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # External APIs
    FOOTBALL_DATA_BASE_URL: str = "http://www.football-data.co.uk"
    UNDERSTAT_API_URL: str = "https://understat.com"
    FBREF_BASE_URL: str = "https://fbref.com"
    
    # ML
    MODEL_DIR: str = "./models"
    RANDOM_STATE: int = 42
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()