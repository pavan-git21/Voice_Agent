import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    # Speech
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-1")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "alloy")

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./appointments.db")

    # Latency budget (ms)
    STT_BUDGET_MS: int = 120
    AGENT_BUDGET_MS: int = 200
    TTS_BUDGET_MS: int = 100
    TOTAL_BUDGET_MS: int = 450

    # Supported languages
    SUPPORTED_LANGUAGES: list = ["en", "hi", "ta"]


settings = Settings()
