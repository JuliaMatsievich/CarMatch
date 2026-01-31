from pydantic_settings import BaseSettings

# psycopg3 — обходит UnicodeDecodeError psycopg2 на Windows при подключении к БД
DEFAULT_DATABASE_URL = "postgresql+psycopg://carmatch:carmatch@localhost:5432/carmatch"
DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"


class Settings(BaseSettings):
    database_url: str = DEFAULT_DATABASE_URL
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = DEFAULT_CORS_ORIGINS
    # GigaChat API (authorization key from https://developers.sber.ru/studio/)
    gigachat_credentials: str = ""
    gigachat_verify_ssl_certs: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"

    def get_database_url(self) -> str:
        """URL для подключения к БД: только ASCII, psycopg3 требует postgresql+psycopg://."""
        url = self.database_url
        if not url.isascii():
            return DEFAULT_DATABASE_URL
        # Render Postgres даёт postgresql:// или postgres:// — конвертируем для psycopg3
        if "postgresql+psycopg" not in url:
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg://", 1)
        return url

    def get_cors_origins_list(self) -> list[str]:
        """CORS origins как список (из env через запятую)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
