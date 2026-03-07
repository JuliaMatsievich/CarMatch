"""seed admin user

Revision ID: 10
Revises: 9
Create Date: 2026-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = "10"
down_revision: Union[str, None] = "9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    users = table(
        "users",
        column("email", sa.String),
        column("password_hash", sa.String),
        column("is_active", sa.Boolean),
        column("is_admin", sa.Boolean),
    )

    # Пароль "admin" в bcrypt-хэше.
    # Важно: должен совпадать с ожидаемым паролем админа на фронтенде.
    password_hash = (
        "$2b$12$NaWjjphJE/SLv6OqY6m3ZOyJZ0ViB1u2iqP/MX3E4D96H1VxNoEuO"
    )

    conn = op.get_bind()
    existing = conn.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": "admin@mail.ru"},
    ).first()
    if existing is None:
        op.execute(
            users.insert().values(
                email="admin@mail.ru",
                password_hash=password_hash,
                is_active=True,
                is_admin=True,
            )
        )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM users WHERE email = :email"),
        {"email": "admin@mail.ru"},
    )

