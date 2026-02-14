"""transmission -> modification, add transmission (gearbox)

Revision ID: 6
Revises: 5
Create Date: 2026-02-14

- Переименовываем колонку transmission в modification (полная строка модификации).
- Добавляем колонку transmission (тип коробки: MT, AMT, CVT и т.д.).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "6"
down_revision: Union[str, None] = "5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Переименовать старую колонку transmission в modification
    op.alter_column(
        "cars",
        "transmission",
        new_column_name="modification",
        existing_type=sa.String(30),
        existing_nullable=True,
    )
    op.alter_column(
        "cars",
        "modification",
        type_=sa.String(100),
        existing_nullable=True,
    )
    # Добавить новую колонку transmission для типа коробки (MT, AMT, ...)
    op.add_column(
        "cars",
        sa.Column("transmission", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cars", "transmission")
    op.alter_column(
        "cars",
        "modification",
        new_column_name="transmission",
        existing_type=sa.String(30),
        existing_nullable=True,
    )
