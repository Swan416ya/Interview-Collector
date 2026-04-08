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
    ai_base_url: str = os.getenv("AI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    ai_model: str = os.getenv("AI_MODEL", "")
    ai_api_key: str = os.getenv("AI_API_KEY", "")
    ai_timeout_seconds: int = int(os.getenv("AI_TIMEOUT_SECONDS", "60"))
    ai_read_timeout_seconds: int = int(os.getenv("AI_READ_TIMEOUT_SECONDS", "120"))
    ai_connect_timeout_seconds: int = int(os.getenv("AI_CONNECT_TIMEOUT_SECONDS", "15"))
    ai_retries: int = int(os.getenv("AI_RETRIES", "2"))
    ai_max_output_tokens: int = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "1200"))
    ai_debug_raw_response: bool = os.getenv("AI_DEBUG_RAW_RESPONSE", "false").lower() == "true"
    ai_thinking_type: str = os.getenv("AI_THINKING_TYPE", "disabled")


settings = Settings()

