"""sessions, chat_messages, cars, search_parameters

Revision ID: 2
Revises: 1
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "2"
down_revision: Union[str, None] = "1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("extracted_params", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("search_criteria", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("search_results", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("message_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("parameters_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cars_found", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"], unique=False)
    op.create_index("idx_sessions_status", "sessions", ["status"], unique=False)
    op.create_index("idx_sessions_created_at", "sessions", ["created_at"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_chat_messages_session_id", "chat_messages", ["session_id"], unique=False)
    op.create_index("idx_chat_messages_sequence", "chat_messages", ["session_id", "sequence_order"], unique=False)

    op.create_table(
        "cars",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(20), server_default="yandex", nullable=False),
        sa.Column("source_id", sa.String(100), nullable=True),
        sa.Column("mark_name", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("body_type", sa.String(50), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("price_rub", sa.Numeric(12, 2), nullable=True),
        sa.Column("fuel_type", sa.String(30), nullable=True),
        sa.Column("engine_volume", sa.Numeric(4, 2), nullable=True),
        sa.Column("horsepower", sa.Integer(), nullable=True),
        sa.Column("transmission", sa.String(30), nullable=True),
        sa.Column("specs", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("images", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("imported_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cars_mark_model", "cars", ["mark_name", "model_name"], unique=False)
    op.create_index("idx_cars_year", "cars", ["year"], unique=False)
    op.create_index("idx_cars_price", "cars", ["price_rub"], unique=False)
    op.create_index("idx_cars_body_type", "cars", ["body_type"], unique=False)
    op.create_index("idx_cars_fuel_type", "cars", ["fuel_type"], unique=False)
    op.create_index("idx_cars_is_active", "cars", ["is_active"], unique=False, postgresql_where=sa.text("is_active = true"))

    op.create_table(
        "search_parameters",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("param_type", sa.String(50), nullable=False),
        sa.Column("param_value", sa.String(255), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_search_parameters_session_id", "search_parameters", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_search_parameters_session_id", table_name="search_parameters")
    op.drop_table("search_parameters")
    op.drop_index("idx_cars_is_active", table_name="cars")
    op.drop_index("idx_cars_fuel_type", table_name="cars")
    op.drop_index("idx_cars_body_type", table_name="cars")
    op.drop_index("idx_cars_price", table_name="cars")
    op.drop_index("idx_cars_year", table_name="cars")
    op.drop_index("idx_cars_mark_model", table_name="cars")
    op.drop_table("cars")
    op.drop_index("idx_chat_messages_sequence", table_name="chat_messages")
    op.drop_index("idx_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("idx_sessions_created_at", table_name="sessions")
    op.drop_index("idx_sessions_status", table_name="sessions")
    op.drop_index("idx_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
