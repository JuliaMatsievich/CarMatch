import asyncio
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy import engine_from_config
from sqlalchemy import MetaData
from alembic import context

from src.config import settings
from src.database import Base
from src.models import User, Session, ChatMessage, Car, SearchParameter  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.get_database_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from sqlalchemy import create_engine
    # Таймауты: при зависании (сеть, блокировка БД) в логах будет ошибка, а не вечное ожидание
    connectable = create_engine(
        settings.get_database_url(),
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": 15},
    )

    with connectable.connect() as connection:
        # Ограничить время выполнения одного запроса (в т.ч. ожидание lock)
        connection.execute(text("SET statement_timeout = '120000'"))  # 120 сек
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
