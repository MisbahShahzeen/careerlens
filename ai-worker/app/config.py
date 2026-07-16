from dotenv import load_dotenv
import os

load_dotenv(override=False)

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")

settings = Settings()