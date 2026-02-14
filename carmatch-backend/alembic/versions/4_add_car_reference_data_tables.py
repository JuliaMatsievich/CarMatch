"""add car reference data tables

Revision ID: 4
Revises: 3
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "4"
down_revision: Union[str, None] = "3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create car_brands table
    op.create_table(
        "car_brands",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name")
    )
    op.create_index(op.f("ix_car_brands_id"), "car_brands", ["id"], unique=False)
    op.create_index(op.f("idx_car_brands_name"), "car_brands", ["name"], unique=False)

    # Create car_models table
    op.create_table(
        "car_models",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["car_brands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_car_models_id"), "car_models", ["id"], unique=False)
    op.create_index(op.f("idx_car_models_brand"), "car_models", ["brand_id"], unique=False)
    op.create_index(op.f("idx_car_models_name"), "car_models", ["name"], unique=False)
    op.create_index(op.f("idx_car_models_external_id"), "car_models", ["external_id"], unique=False)

    # Create car_generations table
    op.create_table(
        "car_generations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("years", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["car_models.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_car_generations_id"), "car_generations", ["id"], unique=False)
    op.create_index(op.f("idx_car_generations_model"), "car_generations", ["model_id"], unique=False)
    op.create_index(op.f("idx_car_generations_external_id"), "car_generations", ["external_id"], unique=False)

    # Create car_modifications table
    op.create_table(
        "car_modifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("generation_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("body_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["generation_id"], ["car_generations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_car_modifications_id"), "car_modifications", ["id"], unique=False)
    op.create_index(op.f("idx_car_modifications_generation"), "car_modifications", ["generation_id"], unique=False)
    op.create_index(op.f("idx_car_modifications_external_id"), "car_modifications", ["external_id"], unique=False)

    # Create car_complectations table
    op.create_table(
        "car_complectations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("modification_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["modification_id"], ["car_modifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_car_complectations_id"), "car_complectations", ["id"], unique=False)
    op.create_index(op.f("idx_car_complectations_modification"), "car_complectations", ["modification_id"], unique=False)
    op.create_index(op.f("idx_car_complectations_external_id"), "car_complectations", ["external_id"], unique=False)

    # Add foreign key columns to cars table
    op.add_column("cars", sa.Column("brand_id", sa.Integer(), nullable=True))
    op.add_column("cars", sa.Column("model_id", sa.Integer(), nullable=True))
    op.add_column("cars", sa.Column("generation_id", sa.Integer(), nullable=True))
    op.add_column("cars", sa.Column("modification_id", sa.Integer(), nullable=True))

    # Create indexes for the new foreign key columns
    op.create_index(op.f("idx_cars_brand"), "cars", ["brand_id"], unique=False)
    op.create_index(op.f("idx_cars_model"), "cars", ["model_id"], unique=False)
    op.create_index(op.f("idx_cars_generation"), "cars", ["generation_id"], unique=False)
    op.create_index(op.f("idx_cars_modification"), "cars", ["modification_id"], unique=False)

    # Add foreign key constraints to cars table
    op.create_foreign_key("fk_cars_brand_id", "cars", "car_brands", ["brand_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_cars_model_id", "cars", "car_models", ["model_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_cars_generation_id", "cars", "car_generations", ["generation_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_cars_modification_id", "cars", "car_modifications", ["modification_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    # Drop foreign key constraints from cars table
    op.drop_constraint("fk_cars_modification_id", "cars", type_="foreignkey")
    op.drop_constraint("fk_cars_generation_id", "cars", type_="foreignkey")
    op.drop_constraint("fk_cars_model_id", "cars", type_="foreignkey")
    op.drop_constraint("fk_cars_brand_id", "cars", type_="foreignkey")

    # Drop indexes for foreign key columns
    op.drop_index(op.f("idx_cars_modification"), table_name="cars")
    op.drop_index(op.f("idx_cars_generation"), table_name="cars")
    op.drop_index(op.f("idx_cars_model"), table_name="cars")
    op.drop_index(op.f("idx_cars_brand"), table_name="cars")

    # Drop columns from cars table
    op.drop_column("cars", "modification_id")
    op.drop_column("cars", "generation_id")
    op.drop_column("cars", "model_id")
    op.drop_column("cars", "brand_id")

    # Drop car_complectations table
    op.drop_index(op.f("ix_car_complectations_id"), table_name="car_complectations")
    op.drop_index(op.f("idx_car_complectations_external_id"), table_name="car_complectations")
    op.drop_index(op.f("idx_car_complectations_modification"), table_name="car_complectations")
    op.drop_table("car_complectations")

    # Drop car_modifications table
    op.drop_index(op.f("ix_car_modifications_id"), table_name="car_modifications")
    op.drop_index(op.f("idx_car_modifications_external_id"), table_name="car_modifications")
    op.drop_index(op.f("idx_car_modifications_generation"), table_name="car_modifications")
    op.drop_table("car_modifications")

    # Drop car_generations table
    op.drop_index(op.f("ix_car_generations_id"), table_name="car_generations")
    op.drop_index(op.f("idx_car_generations_external_id"), table_name="car_generations")
    op.drop_index(op.f("idx_car_generations_model"), table_name="car_generations")
    op.drop_table("car_generations")

    # Drop car_models table
    op.drop_index(op.f("ix_car_models_id"), table_name="car_models")
    op.drop_index(op.f("idx_car_models_external_id"), table_name="car_models")
    op.drop_index(op.f("idx_car_models_name"), table_name="car_models")
    op.drop_index(op.f("idx_car_models_brand"), table_name="car_models")
    op.drop_table("car_models")

    # Drop car_brands table
    op.drop_index(op.f("ix_car_brands_id"), table_name="car_brands")
    op.drop_index(op.f("idx_car_brands_name"), table_name="car_brands")
    op.drop_table("car_brands")