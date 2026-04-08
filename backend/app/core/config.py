import os

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Interview Collector API")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    app_env: str = os.getenv("APP_ENV", "dev")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./interview_collector.db")
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]


settings = Settings()

