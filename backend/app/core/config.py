from dotenv import load_dotenv
import os

load_dotenv(override=False)

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    MONGODB_URL: str = os.getenv("MONGODB_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "changethisinproduction")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    AI_WORKER_URL: str = os.getenv("AI_WORKER_URL", "http://localhost:8001")

settings = Settings()