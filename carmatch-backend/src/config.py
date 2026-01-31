from pydantic_settings import BaseSettings

# psycopg3 — обходит UnicodeDecodeError psycopg2 на Windows при подключении к БД
DEFAULT_DATABASE_URL = "postgresql+psycopg://carmatch:carmatch@localhost:5432/carmatch"


class Settings(BaseSettings):
    database_url: str = DEFAULT_DATABASE_URL
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    class Config:
        env_file = ".env"
        extra = "ignore"

    def get_database_url(self) -> str:
        """URL для подключения к БД: только ASCII, чтобы избежать ошибок psycopg2 на Windows."""
        url = self.database_url
        if not url.isascii():
            return DEFAULT_DATABASE_URL
        return url


settings = Settings()
