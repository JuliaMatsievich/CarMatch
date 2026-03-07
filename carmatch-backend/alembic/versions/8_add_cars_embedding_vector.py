"""Add pgvector extension and cars.embedding column for vector search

Revision ID: 8
Revises: 7
Create Date: 2026-02-15

Колонка embedding — вектор эмбеддинга (модель Яндекса, размерность 256).
Таблицу cars.xml не трогаем; изменения только в БД.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "8"
down_revision: Union[str, None] = "7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        "ALTER TABLE cars ADD COLUMN IF NOT EXISTS embedding vector(256) NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE cars DROP COLUMN IF EXISTS embedding")
