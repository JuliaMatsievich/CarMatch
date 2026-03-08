"""update admin password to admin1234

Revision ID: 11
Revises: 10
Create Date: 2026-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "11"
down_revision: Union[str, None] = "10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
UPDATE users
SET password_hash = :hash
WHERE email = :email
"""
        ).bindparams(
            hash="$2b$12$NoRgJhr9dHT7npSV4EH7GOjZ98F3bYF576ddozb7oQeXo8Zrm/9RG",
            email="admin@mail.ru",
        )
    )


def downgrade() -> None:
  # В downgrade пароль не восстанавливаем (не критично для отката схемы).
  pass

