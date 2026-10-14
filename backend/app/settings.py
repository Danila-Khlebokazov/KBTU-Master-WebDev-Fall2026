from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Expense Tracker API"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    POSTGRES_USER: str = "expenses"
    POSTGRES_PASSWORD: str = "expenses"
    POSTGRES_DB: str = "expenses"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin12345"
    ADMIN_FULL_NAME: str = "Administrator"

    SEED_DEMO_DATA: bool = True
    DEMO_USER_PASSWORD: str = "demo12345"

    # Comma-separated list, e.g. "http://localhost:8080,http://127.0.0.1:8080"
    CORS_ORIGINS: str = "http://localhost:8080"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
