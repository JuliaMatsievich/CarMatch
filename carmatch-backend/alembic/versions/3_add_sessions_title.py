"""add sessions title

Revision ID: 3
Revises: 2
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "3"
down_revision: Union[str, None] = "2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("title", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "title")
