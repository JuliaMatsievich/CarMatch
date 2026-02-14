"""cars description: mark model (transmission), body_type, year. facts

Revision ID: 5
Revises: 4
Create Date: 2026-02-14

Обновляет поле description в таблице cars до формата:
mark_name model_name (transmission), body_type, year. <текущие факты из description>
"""
from typing import Sequence, Union

from alembic import op

revision: str = "5"
down_revision: Union[str, None] = "4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Формат: mark_name model_name (transmission), body_type, year. старый_description
    op.execute("""
        UPDATE cars SET description = trim(BOTH ', ' FROM (
            mark_name || ' ' || model_name
            || CASE WHEN transmission IS NOT NULL AND trim(transmission) <> '' THEN ' (' || transmission || ')' ELSE '' END
            || CASE WHEN body_type IS NOT NULL AND trim(body_type) <> '' THEN ', ' || body_type ELSE '' END
            || CASE WHEN year IS NOT NULL THEN ', ' || year::text ELSE '' END
            || CASE WHEN description IS NOT NULL AND trim(description) <> '' THEN '. ' || trim(description) ELSE '' END
        ))
    """)


def downgrade() -> None:
    # Откатить нельзя: старые значения description потеряны
    pass
