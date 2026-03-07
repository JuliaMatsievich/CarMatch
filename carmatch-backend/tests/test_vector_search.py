"""Tests for vector search and hybrid ranking service."""

from __future__ import annotations

from typing import Any, Iterable, List, Tuple

import pytest
from sqlalchemy.orm import Session

from src.models import Car
from src.services import vector_search


def create_car(db: Session, **overrides: Any) -> Car:
    """Helper to create and persist a Car in the test DB."""
    car = Car(
        mark_name=overrides.get("mark_name", "Toyota"),
        model_name=overrides.get("model_name", "Camry"),
        body_type=overrides.get("body_type"),
        year=overrides.get("year"),
        price_rub=overrides.get("price_rub"),
        fuel_type=overrides.get("fuel_type"),
        engine_volume=overrides.get("engine_volume"),
        horsepower=overrides.get("horsepower"),
        transmission=overrides.get("transmission"),
        country=overrides.get("country"),
        specs=overrides.get("specs", {}),
        is_active=overrides.get("is_active", True),
    )
    db.add(car)
    db.commit()
    db.refresh(car)
    return car


def test_compose_search_query_includes_params_and_message():
    params = {
        "brand": "Toyota",
        "model": "Camry",
        "body_type": "седан",
        "year": 2020,
        "fuel_type": "бензин",
        "transmission": "автомат",
        "engine_volume": 2.5,
        "horsepower": 181,
        "modification": "2.5 AT",
    }
    msg = "Хочу надёжную машину для семьи"

    query = vector_search.compose_search_query(params, last_user_message=msg)

    assert "Toyota" in query
    assert "Camry" in query
    assert "седан" in query
    assert "2020 год" in query
    assert "бензин" in query
    assert "автомат" in query
    assert "2.5 л" in query
    assert "181 л.с." in query
    assert "2.5 AT" in query
    assert msg in query


def test_compose_search_query_uses_message_when_no_params():
    msg = "Просто хочу электромобиль для города"
    query = vector_search.compose_search_query({}, last_user_message=msg)
    assert query == msg


def test_compose_search_query_trims_and_limits_message_length():
    long_msg = "x" * 500
    query = vector_search.compose_search_query({}, last_user_message="  " + long_msg + "  ")
    assert len(query) == 200
    assert set(query) == {"x"}


def test_sql_search_cars_filters_by_brand_model_and_case_insensitive(db: Session):
    target = create_car(
        db,
        mark_name="Toyota",
        model_name="Camry",
        body_type="седан",
    )
    other = create_car(
        db,
        mark_name="BMW",
        model_name="X5",
        body_type="внедорожник",
    )

    cars = vector_search.sql_search_cars(
        db,
        params={"brand": "toyota", "model": "cam"},
        limit=10,
    )

    assert target in cars
    assert other not in cars


def test_sql_search_cars_applies_year_range_and_engine_volume(db: Session):
    in_range = create_car(db, year=2020, engine_volume=2.0)
    out_of_year = create_car(db, year=2010, engine_volume=2.0)
    out_of_volume = create_car(db, year=2020, engine_volume=3.0)

    cars = vector_search.sql_search_cars(
        db,
        params={"year_min": 2019, "year_max": 2021, "engine_volume": 2.0},
        limit=10,
    )
    assert in_range in cars
    assert out_of_year not in cars
    assert out_of_volume not in cars


def test_compute_param_match_fraction_full_match():
    car = Car(
        mark_name="Toyota",
        model_name="Camry",
        body_type="седан",
        fuel_type="бензин",
        transmission="автомат",
        year=2020,
        horsepower=180,
        engine_volume=2.5,
        specs={},
        source="yandex",
        is_active=True,
    )

    params = {
        "brand": "Toyota",
        "model": "Camry",
        "body_type": "седан",
        "fuel_type": "бензин",
        "transmission": "автомат",
        "year": 2020,
        "horsepower": 180,
        "engine_volume": 2.5,
    }

    fraction = vector_search.compute_param_match_fraction(car, params)
    assert fraction == pytest.approx(1.0)


def test_compute_param_match_fraction_with_tolerances():
    car = Car(
        mark_name="Toyota",
        model_name="Camry",
        body_type="седан",
        fuel_type="бензин",
        transmission="автомат",
        year=2021,  # допуск ±1 год
        horsepower=200,  # в пределах ±10% от 180
        engine_volume=2.6,  # в пределах ±0.1 от 2.5
        specs={},
        source="yandex",
        is_active=True,
    )
    params = {
        "brand": "Toyota",
        "model": "Camry",
        "body_type": "седан",
        "fuel_type": "бензин",
        "transmission": "автомат",
        "year": 2020,
        "horsepower": 180,
        "engine_volume": 2.5,
    }

    fraction = vector_search.compute_param_match_fraction(car, params)
    # С учётом допусков ожидаем неполное, но существенно положительное совпадение.
    assert 0.5 <= fraction <= 1.0


def test_hybrid_rank_fallback_uses_param_fraction_without_semantic(db: Session):
    car = create_car(
        db,
        mark_name="Toyota",
        model_name="Camry",
        body_type="седан",
        fuel_type="бензин",
        horsepower=180,
    )
    params = {"brand": "Toyota", "body_type": "седан", "fuel_type": "бензин"}

    ranked: List[Tuple[Car, float]] = vector_search.hybrid_rank(
        semantic_results=[],
        sql_cars=[car],
        params=params,
        threshold=0.9,  # высокий порог, но в fallback он не используется
    )

    assert len(ranked) == 1
    ranked_car, score = ranked[0]
    assert ranked_car.id == car.id
    assert 0.0 < score <= 1.0


def test_hybrid_rank_combines_semantic_and_param_scores(db: Session):
    car = create_car(
        db,
        mark_name="Toyota",
        model_name="Camry",
        body_type="седан",
        fuel_type="бензин",
    )
    params = {"brand": "Toyota", "body_type": "седан"}

    semantic_results: Iterable[Tuple[Car, float]] = [(car, 0.5)]
    sql_cars = [car]

    ranked = vector_search.hybrid_rank(
        semantic_results=semantic_results,
        sql_cars=sql_cars,
        params=params,
        w1=0.6,
        w2=0.4,
        threshold=0.3,
    )

    assert len(ranked) == 1
    ranked_car, score = ranked[0]
    assert ranked_car.id == car.id
    assert score == pytest.approx(0.6 * 0.5 + 0.4 * 1.0)


def test_vector_search_cars_empty_query_returns_empty_list(db: Session):
    results = vector_search.vector_search_cars(db, query_text="  ")
    assert results == []


def test_vector_search_cars_get_embedding_none_returns_empty_list(
    db: Session, monkeypatch: pytest.MonkeyPatch
):
    def fake_get_query_embedding(_: str):
        return None

    monkeypatch.setattr(vector_search, "get_query_embedding", fake_get_query_embedding)
    results = vector_search.vector_search_cars(db, query_text="Toyota Camry")
    assert results == []


def test_vector_search_cars_success_path_uses_db_execute_and_returns_cars(
    monkeypatch: pytest.MonkeyPatch,
):
    car1 = Car(
        id=1,
        mark_name="Toyota",
        model_name="Camry",
        specs={},
        source="yandex",
        is_active=True,
    )
    car2 = Car(
        id=2,
        mark_name="Toyota",
        model_name="RAV4",
        specs={},
        source="yandex",
        is_active=True,
    )

    def fake_get_query_embedding(_: str):
        return [0.1, 0.2, 0.3]

    class FakeResult:
        def __init__(self, rows: list[tuple[int]]):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class FakeQuery:
        def __init__(self, cars_by_id: dict[int, Car]):
            self._cars_by_id = cars_by_id

        def filter(self, *_, **__):
            return self

        def all(self):
            return list(self._cars_by_id.values())

    class FakeSession:
        def __init__(self, cars: list[Car]):
            self._cars_by_id = {c.id: c for c in cars}

        def execute(self, statement, params=None, **kwargs):
            assert "FROM cars" in str(statement)
            assert "ORDER BY embedding <=>" in str(statement)
            assert "LIMIT" in str(statement)
            assert "qv" in params
            assert "lim" in params
            # Имитация того, что pgvector вернул id в нужном порядке
            return FakeResult([(1,), (2,)])

        def query(self, model):
            assert model is Car
            return FakeQuery(self._cars_by_id)

    fake_db = FakeSession([car1, car2])

    monkeypatch.setattr(vector_search, "get_query_embedding", fake_get_query_embedding)

    results = vector_search.vector_search_cars(fake_db, query_text="Toyota")
    assert [c.id for c in results] == [1, 2]


def test_vector_search_cars_pgvector_error_returns_empty_list(
    db: Session, monkeypatch: pytest.MonkeyPatch
):
    car = create_car(db, mark_name="Toyota", model_name="Camry")

    def fake_get_query_embedding(_: str):
        return [0.1, 0.2]

    def fake_execute(*_, **__):
        raise RuntimeError("pgvector error")

    monkeypatch.setattr(vector_search, "get_query_embedding", fake_get_query_embedding)
    monkeypatch.setattr(db, "execute", fake_execute)

    results = vector_search.vector_search_cars(db, query_text="Toyota")
    assert results == []


def test_vector_search_cars_with_scores_returns_normalized_scores(
    monkeypatch: pytest.MonkeyPatch,
):
    car1 = Car(
        id=1,
        mark_name="Toyota",
        model_name="Camry",
        specs={},
        source="yandex",
        is_active=True,
    )
    car2 = Car(
        id=2,
        mark_name="Toyota",
        model_name="RAV4",
        specs={},
        source="yandex",
        is_active=True,
    )

    def fake_get_query_embedding(_: str):
        return [0.1, 0.2, 0.3]

    class FakeResult:
        def __init__(self, rows: list[tuple[int, float]]):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class FakeQuery:
        def __init__(self, cars_by_id: dict[int, Car]):
            self._cars_by_id = cars_by_id

        def filter(self, *_, **__):
            return self

        def all(self):
            return list(self._cars_by_id.values())

    class FakeSession:
        def __init__(self, cars: list[Car]):
            self._cars_by_id = {c.id: c for c in cars}

        def execute(self, statement, params=None, **kwargs):
            assert "SELECT id, (embedding <=>" in str(statement)
            return FakeResult(
                [
                    (1, 0.2),  # ближе (distance меньше)
                    (2, 0.8),
                ]
            )

        def query(self, model):
            assert model is Car
            return FakeQuery(self._cars_by_id)

    fake_db = FakeSession([car1, car2])

    monkeypatch.setattr(vector_search, "get_query_embedding", fake_get_query_embedding)

    results = vector_search.vector_search_cars_with_scores(
        fake_db, query_text="Toyota", limit=2
    )
    assert len(results) == 2
    (r1, score1), (r2, score2) = results
    assert r1.id == car1.id
    assert r2.id == car2.id
    assert 0.0 <= score1 <= 1.0
    assert 0.0 <= score2 <= 1.0
    assert score1 > score2


def test_vector_search_cars_with_scores_pgvector_error_returns_empty_list(
    db: Session, monkeypatch: pytest.MonkeyPatch
):
    create_car(db, mark_name="Toyota", model_name="Camry")

    def fake_get_query_embedding(_: str):
        return [0.1, 0.2]

    def fake_execute(*_, **__):
        raise RuntimeError("pgvector error")

    monkeypatch.setattr(vector_search, "get_query_embedding", fake_get_query_embedding)
    monkeypatch.setattr(db, "execute", fake_execute)

    results = vector_search.vector_search_cars_with_scores(db, query_text="Toyota")
    assert results == []

