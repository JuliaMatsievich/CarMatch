"""Backfill fuel_type, engine_volume, horsepower, transmission from modification

Revision ID: 7
Revises: 6
Create Date: 2026-02-14

Заполняет поля fuel_type, engine_volume, horsepower, transmission
на основе парсинга строки modification (где они ещё пустые).
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from src.utils.modification_parser import parse_modification_string

revision: str = "7"
down_revision: Union[str, None] = "6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Парсим modification и обновляем поля cars (только где они NULL)."""
    conn = op.get_bind()
    rows = conn.execute(
        text(
            "SELECT id, modification, fuel_type, engine_volume, horsepower, transmission FROM cars WHERE modification IS NOT NULL AND trim(modification) <> ''"
        )
    ).fetchall()
    for row in rows:
        car_id, mod_str, ft, ev, hp, tr = row
        parsed = parse_modification_string(mod_str)
        updates = []
        params = {"car_id": car_id}
        if not ft and parsed["fuel_type"]:
            updates.append("fuel_type = :fuel_type")
            params["fuel_type"] = parsed["fuel_type"]
        if ev is None and parsed["engine_volume"] is not None:
            updates.append("engine_volume = :engine_volume")
            params["engine_volume"] = str(parsed["engine_volume"])
        if hp is None and parsed["horsepower"] is not None:
            updates.append("horsepower = :horsepower")
            params["horsepower"] = parsed["horsepower"]
        if not tr and parsed["transmission"]:
            updates.append("transmission = :transmission")
            params["transmission"] = parsed["transmission"]
        if updates:
            conn.execute(
                text("UPDATE cars SET " + ", ".join(updates) + " WHERE id = :car_id"),
                params,
            )


def downgrade() -> None:
    # Откат не обнуляет заполненные поля — при необходимости очистить вручную
    pass
