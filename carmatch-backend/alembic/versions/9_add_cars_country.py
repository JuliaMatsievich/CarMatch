"""Add cars.country column and backfill from description

Revision ID: 9
Revises: 8
Create Date: 2026-02-20

Колонка country — страна-производитель. Заполняется из description
(«Выпускается в X» или «Производство — X»).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "9"
down_revision: Union[str, None] = "8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE cars ADD COLUMN IF NOT EXISTS country VARCHAR(80) NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE cars DROP COLUMN IF EXISTS country")
