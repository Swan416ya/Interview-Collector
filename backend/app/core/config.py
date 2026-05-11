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
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:7357,http://localhost:7357",
        ).split(",")
        if origin.strip()
    ]
    # ark_responses: Volcengine Ark /responses (default). openai_compatible: POST .../chat/completions (e.g. Xiaomi MiMo Token Plan).
    ai_provider: str = os.getenv("AI_PROVIDER", "ark_responses").strip().lower() or "ark_responses"
    ai_base_url: str = os.getenv("AI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    ai_model: str = os.getenv("AI_MODEL", "")
    ai_api_key: str = os.getenv("AI_API_KEY", "")
    ai_timeout_seconds: int = int(os.getenv("AI_TIMEOUT_SECONDS", "60"))
    ai_read_timeout_seconds: int = int(os.getenv("AI_READ_TIMEOUT_SECONDS", "120"))
    ai_connect_timeout_seconds: int = int(os.getenv("AI_CONNECT_TIMEOUT_SECONDS", "15"))
    ai_retries: int = int(os.getenv("AI_RETRIES", "2"))
    ai_max_output_tokens: int = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "1200"))
    ai_kb_max_output_tokens: int = int(os.getenv("AI_KB_MAX_OUTPUT_TOKENS", "2048"))
    ai_session_summary_max_output_tokens: int = int(os.getenv("AI_SESSION_SUMMARY_MAX_OUTPUT_TOKENS", "1500"))
    ai_debug_raw_response: bool = os.getenv("AI_DEBUG_RAW_RESPONSE", "false").lower() == "true"
    ai_thinking_type: str = os.getenv("AI_THINKING_TYPE", "disabled")
    import_preview_cache_enabled: bool = os.getenv("IMPORT_PREVIEW_CACHE_ENABLED", "true").lower() == "true"
    import_preview_cache_ttl_seconds: int = int(os.getenv("IMPORT_PREVIEW_CACHE_TTL_SECONDS", "1800"))
    practice_daily_idempotency_enabled: bool = os.getenv("PRACTICE_DAILY_IDEMPOTENCY_ENABLED", "true").lower() == "true"
    practice_daily_idempotency_seconds: int = int(os.getenv("PRACTICE_DAILY_IDEMPOTENCY_SECONDS", "60"))
    # Wrongbook: admit when ai_score <= max; optional consecutive low scores; discharge after streak of highs
    wrongbook_admit_max_score: int = int(os.getenv("WRONGBOOK_ADMIT_MAX_SCORE", "6"))
    wrongbook_admit_consecutive_low: int = int(os.getenv("WRONGBOOK_ADMIT_CONSECUTIVE_LOW", "1"))
    wrongbook_discharge_min_score: int = int(os.getenv("WRONGBOOK_DISCHARGE_MIN_SCORE", "8"))
    wrongbook_discharge_streak: int = int(os.getenv("WRONGBOOK_DISCHARGE_STREAK", "3"))


settings = Settings()

