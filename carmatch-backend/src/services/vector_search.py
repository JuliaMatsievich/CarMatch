"""
Сервис векторного поиска автомобилей (RAG).
Формирует поисковый запрос из параметров диалога, получает эмбеддинг через Yandex API,
выполняет cosine similarity search по pgvector и возвращает топ-N релевантных Car.
"""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Tuple

from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from src.models import Car
from src.services.yandex_embeddings import get_query_embedding

logger = logging.getLogger(__name__)


def compose_search_query(params: dict, last_user_message: str = "") -> str:
    """
    Формирует текстовый запрос для эмбеддинга из накопленных параметров сессии
    и последнего сообщения пользователя.

    Пример результата:
      "Toyota Camry, седан, 2020 год, бензин, автомат. Хочу надёжную машину для семьи"
    """
    parts: list[str] = []
    if params.get("brand"):
        parts.append(str(params["brand"]).strip())
    if params.get("model"):
        parts.append(str(params["model"]).strip())
    if params.get("body_type"):
        parts.append(str(params["body_type"]).strip())
    if params.get("year"):
        parts.append(f"{params['year']} год")
    if params.get("fuel_type"):
        parts.append(str(params["fuel_type"]).strip())
    if params.get("transmission"):
        parts.append(str(params["transmission"]).strip())
    if params.get("engine_volume"):
        parts.append(f"{params['engine_volume']} л")
    if params.get("horsepower"):
        parts.append(f"{params['horsepower']} л.с.")
    if params.get("modification"):
        parts.append(str(params["modification"]).strip())

    query = ", ".join(parts)

    # Добавляем контекст из последнего сообщения пользователя (обрезаем до 200 символов)
    if last_user_message and last_user_message.strip():
        msg = last_user_message.strip()[:200]
        query = f"{query}. {msg}" if query else msg

    return query.strip()


def vector_search_cars(
    db: Session,
    query_text: str,
    limit: int = 10,
) -> list[Car]:
    """
    Векторный поиск автомобилей по смыслу запроса (cosine distance, pgvector).

    1. Получает query embedding через Yandex API (text-search-query).
    2. Выполняет SELECT ... ORDER BY embedding <=> query LIMIT N.
    3. Возвращает список объектов Car (ORM) или пустой список при ошибке.

    При недоступности Yandex API или отсутствии embeddings — возвращает [],
    чтобы вызывающий код мог переключиться на SQL-fallback.
    """
    if not query_text or not query_text.strip():
        logger.warning("vector_search_cars: пустой query_text, пропускаем")
        return []

    # Шаг 1: получить эмбеддинг запроса
    embedding = get_query_embedding(query_text)
    if embedding is None:
        logger.warning("vector_search_cars: не удалось получить эмбеддинг запроса (Yandex API), fallback на SQL")
        return []

    # Шаг 2: строка вектора для PostgreSQL: '[0.1,0.2,...]'
    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"

    # Шаг 3: cosine similarity search через pgvector
    try:
        rows = db.execute(
            sa_text("""
                SELECT id
                FROM cars
                WHERE is_active = true AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:qv AS vector)
                LIMIT :lim
            """),
            {"qv": vec_str, "lim": limit},
        ).fetchall()
    except Exception as e:
        logger.exception("vector_search_cars: ошибка pgvector запроса: %s", e)
        return []

    if not rows:
        logger.info("vector_search_cars: нет машин с заполненным embedding")
        return []

    # Шаг 4: загрузить полные ORM-объекты Car по найденным id (сохраняя порядок)
    car_ids = [r[0] for r in rows]
    cars_by_id = {
        car.id: car
        for car in db.query(Car).filter(Car.id.in_(car_ids)).all()
    }
    # Возвращаем в порядке cosine distance (порядок из pgvector запроса)
    result = [cars_by_id[cid] for cid in car_ids if cid in cars_by_id]

    logger.info(
        "vector_search_cars: query=%r, найдено=%d авто (limit=%d)",
        query_text[:100],
        len(result),
        limit,
    )
    return result


def _normalize_str(value: str | None) -> str:
    return (value or "").strip().lower()


def _parse_int(value: object) -> int | None:
    try:
        if value is None:
            return None
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _parse_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def vector_search_cars_with_scores(
    db: Session,
    query_text: str,
    limit: int = 20,
) -> List[Tuple[Car, float]]:
    """
    Векторный поиск автомобилей по смыслу запроса (cosine distance, pgvector)
    с возвращением нормализованной косинусной близости (0..1) для каждого авто.
    """
    if not query_text or not query_text.strip():
        logger.warning("vector_search_cars_with_scores: пустой query_text, пропускаем")
        return []

    embedding = get_query_embedding(query_text)
    if embedding is None:
        logger.warning(
            "vector_search_cars_with_scores: не удалось получить эмбеддинг запроса (Yandex API)"
        )
        return []

    vec_str = "[" + ",".join(str(x) for x in embedding) + "]"

    try:
        rows = db.execute(
            sa_text(
                """
                SELECT id, (embedding <=> CAST(:qv AS vector)) AS distance
                FROM cars
                WHERE is_active = true AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:qv AS vector)
                LIMIT :lim
            """
            ),
            {"qv": vec_str, "lim": limit},
        ).fetchall()
    except Exception as e:  # noqa: BLE001
        logger.exception("vector_search_cars_with_scores: ошибка pgvector запроса: %s", e)
        return []

    if not rows:
        logger.info("vector_search_cars_with_scores: нет машин с заполненным embedding")
        return []

    car_ids = [int(r[0]) for r in rows]
    id_to_distance: Dict[int, float] = {int(r[0]): float(r[1]) for r in rows}

    cars_by_id = {
        car.id: car for car in db.query(Car).filter(Car.id.in_(car_ids)).all()
    }

    result: List[Tuple[Car, float]] = []
    for cid in car_ids:
        car = cars_by_id.get(cid)
        if not car:
            continue
        distance = id_to_distance.get(cid, 1.0)
        raw_sim = 1.0 - float(distance)
        norm_sim = (raw_sim + 1.0) / 2.0
        if norm_sim < 0.0:
            norm_sim = 0.0
        elif norm_sim > 1.0:
            norm_sim = 1.0
        result.append((car, norm_sim))

    logger.info(
        "vector_search_cars_with_scores: query=%r, найдено=%d авто (limit=%d)",
        query_text[:100],
        len(result),
        limit,
    )
    return result


def sql_search_cars(
    db: Session,
    params: dict,
    limit: int = 50,
) -> List[Car]:
    """
    Поиск автомобилей по параметрам в SQL с допуском для числовых полей.

    - brand, model, country, body_type, fuel_type — ILIKE '%value%' (если указаны).
    - year / year_min / year_max — допуск по году: year BETWEEN (min - 1) AND (max + 1).
    - horsepower — допуск по мощности: ±10% (но не меньше ±5 л.с.).
    - engine_volume — допуск по объёму: ±0.1 л.
    """
    q = db.query(Car).filter(Car.is_active.is_(True))

    brand = _normalize_str(params.get("brand"))
    if brand:
        q = q.filter(Car.mark_name.ilike(f"%{brand}%"))

    model = _normalize_str(params.get("model"))
    if model:
        q = q.filter(Car.model_name.ilike(f"%{model}%"))

    country = _normalize_str(params.get("country"))
    if country:
        q = q.filter(Car.country.ilike(f"%{country}%"))

    body_type = _normalize_str(params.get("body_type"))
    if body_type:
        q = q.filter(Car.body_type.ilike(f"%{body_type}%"))

    fuel_type = _normalize_str(params.get("fuel_type"))
    if fuel_type:
        q = q.filter(Car.fuel_type.ilike(f"%{fuel_type}%"))

    transmission = _normalize_str(params.get("transmission"))
    if transmission:
        q = q.filter(Car.transmission.ilike(f"%{transmission}%"))

    # Год выпуска: поддержка year, year_min, year_max
    year = _parse_int(params.get("year"))
    year_min = _parse_int(params.get("year_min"))
    year_max = _parse_int(params.get("year_max"))

    # Если задан конкретный год — ищем по нему (при желании можно дать небольшой допуск, но без сжатия диапазона к середине).
    if year is not None and year_min is None and year_max is None:
        year_min = year
        year_max = year

    if year_min is not None:
        q = q.filter(Car.year >= year_min)
    if year_max is not None:
        q = q.filter(Car.year <= year_max)

    # Мощность (л.с.): поддержка horsepower, power_min, power_max
    horsepower = _parse_int(params.get("horsepower"))
    power_min = _parse_int(params.get("power_min"))
    power_max = _parse_int(params.get("power_max"))
    if horsepower is not None:
        power_min = power_min or horsepower
        power_max = power_max or horsepower
    if power_min is not None or power_max is not None:
        p_min = float(power_min or power_max)
        p_max = float(power_max or power_min)
        center = (p_min + p_max) / 2.0
        delta = max(5.0, center * 0.1)
        hp_min = int(center - delta)
        hp_max = int(center + delta)
        q = q.filter(Car.horsepower >= hp_min, Car.horsepower <= hp_max)

    # Объём двигателя (л) с небольшим допуском
    engine_volume = _parse_float(params.get("engine_volume"))
    if engine_volume is not None:
        ev_min = engine_volume - 0.1
        ev_max = engine_volume + 0.1
        q = q.filter(Car.engine_volume >= ev_min, Car.engine_volume <= ev_max)

    cars = q.limit(limit).all()
    logger.info(
        "sql_search_cars: params_keys=%s, найдено=%d авто (limit=%d)",
        [k for k, v in params.items() if v],
        len(cars),
        limit,
    )
    return cars


def compute_param_match_fraction(car: Car, params: dict) -> float:
    """
    Вычисляет долю совпавших параметров из запроса для конкретного автомобиля.

    Учитываются только параметры, которые не равны null/пустой строке.
    """
    if not params:
        return 0.0

    total = 0
    matched = 0

    brand = _normalize_str(params.get("brand"))
    if brand:
        total += 1
        if brand in _normalize_str(getattr(car, "mark_name", None)):
            matched += 1

    model = _normalize_str(params.get("model"))
    if model:
        total += 1
        if model in _normalize_str(getattr(car, "model_name", None)):
            matched += 1

    country = _normalize_str(params.get("country"))
    if country:
        total += 1
        if country in _normalize_str(getattr(car, "country", None)):
            matched += 1

    body_type = _normalize_str(params.get("body_type"))
    if body_type:
        total += 1
        if body_type in _normalize_str(getattr(car, "body_type", None)):
            matched += 1

    fuel_type = _normalize_str(params.get("fuel_type"))
    if fuel_type:
        total += 1
        if fuel_type in _normalize_str(getattr(car, "fuel_type", None)):
            matched += 1

    transmission = _normalize_str(params.get("transmission"))
    if transmission:
        total += 1
        if transmission in _normalize_str(getattr(car, "transmission", None)):
            matched += 1

    year = _parse_int(params.get("year"))
    if year is not None:
        total += 1
        car_year = _parse_int(getattr(car, "year", None))
        if car_year is not None and abs(car_year - year) <= 1:
            matched += 1

    horsepower = _parse_int(params.get("horsepower"))
    if horsepower is not None:
        total += 1
        car_hp = _parse_int(getattr(car, "horsepower", None))
        if car_hp is not None:
            delta = max(5, int(horsepower * 0.1))
            if abs(car_hp - horsepower) <= delta:
                matched += 1

    engine_volume = _parse_float(params.get("engine_volume"))
    if engine_volume is not None:
        total += 1
        car_ev = _parse_float(getattr(car, "engine_volume", None))
        if car_ev is not None and abs(car_ev - engine_volume) <= 0.1:
            matched += 1

    if total == 0:
        return 0.0
    return matched / total


def hybrid_rank(
    semantic_results: Iterable[Tuple[Car, float]],
    sql_cars: Iterable[Car],
    params: dict,
    w1: float = 0.6,
    w2: float = 0.4,
    threshold: float = 0.6,
) -> List[Tuple[Car, float]]:
    """
    Гибридное ранжирование:
    score = w1 * (семантическая_близость) + w2 * (доля_совпавших_параметров).
    """
    id_to_sem_sim: Dict[int, float] = {}
    id_to_car: Dict[int, Car] = {}

    has_semantic = False
    for car, sim in semantic_results or []:
        if not isinstance(car, Car) or car.id is None:
            continue
        cid = int(car.id)
        id_to_sem_sim[cid] = float(sim)
        id_to_car[cid] = car
        has_semantic = True

    has_sql = False
    for car in sql_cars or []:
        if not isinstance(car, Car) or car.id is None:
            continue
        cid = int(car.id)
        if cid not in id_to_car:
            id_to_car[cid] = car
        has_sql = True

    if not id_to_car:
        return []

    ranked: List[Tuple[Car, float]] = []
    # Режим fallback: нет семантических кандидатов, но есть результаты SQL.
    # В этом случае используем чисто параметрический скор (без порога),
    # чтобы не «терять» машины, найденные по фильтрам.
    if not has_semantic and has_sql:
        for cid, car in id_to_car.items():
            param_fraction = compute_param_match_fraction(car, params)
            if param_fraction <= 0.0:
                continue
            ranked.append((car, float(param_fraction)))
    else:
        for cid, car in id_to_car.items():
            sem_sim = id_to_sem_sim.get(cid, 0.0)
            param_fraction = compute_param_match_fraction(car, params)
            score = w1 * sem_sim + w2 * param_fraction
            if score >= threshold:
                ranked.append((car, score))

    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked
