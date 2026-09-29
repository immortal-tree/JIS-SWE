"""Settings, read from environment variables (or a .env file in the project root)."""

import os

from dotenv import load_dotenv

load_dotenv()  # never overrides variables that are already set


class Settings:
    def __init__(self) -> None:
        self.database_url: str = os.environ.get(
            "DATABASE_URL", "postgresql://jis:jis_password@localhost:5432/jis"
        )
        self.jwt_secret: str = os.environ.get("JWT_SECRET", "")
        self.jwt_expire_minutes: int = int(os.environ.get("JWT_EXPIRE_MINUTES", "480"))
        self.cors_origins: list[str] = [
            o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()
        ]


settings = Settings()
