"""Роутер поиска автомобилей."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.deps import get_current_user
from src.database import get_db
from src.models import User
from src.schemas import CarResult, CarSearchResponse
from src.services.reference_data.car_reference_service import search_cars as search_cars_service

router = APIRouter(prefix="/cars", tags=["cars"])


def _car_to_result(c):
    return CarResult(
        id=c.id,
        mark_name=c.mark_name,
        model_name=c.model_name,
        year=c.year,
        price_rub=float(c.price_rub) if c.price_rub is not None else None,
        body_type=c.body_type,
        fuel_type=c.fuel_type,
        engine_volume=float(c.engine_volume) if c.engine_volume is not None else None,
        horsepower=c.horsepower,
        modification=getattr(c, "modification", None) or None,
        transmission=c.transmission,
        images=list(c.images) if c.images else [],
        description=getattr(c, "description", None) or None,
        brand_id=c.brand_id,
        model_id=c.model_id,
        generation_id=c.generation_id,
        modification_id=c.modification_id,
    )


@router.get("/search", response_model=CarSearchResponse)
def search_cars(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    brand: str | None = Query(None, description="Марка (из справочника car_brands)"),
    model: str | None = Query(None, description="Модель (из справочника car_models)"),
    body_type: str | None = Query(None, description="Тип кузова (точное значение из справочника)"),
    year: int | None = Query(None, description="Год выпуска"),
    modification: str | None = Query(None, description="Модификация (подстрока: объём, коробка, мощность)"),
    transmission: str | None = Query(None, description="Тип коробки (MT, AMT, CVT и т.д.)"),
    fuel_type: str | None = Query(None, description="Тип топлива: бензин, дизель, гибрид, электро"),
    engine_volume: float | None = Query(None, description="Объём двигателя (л, например 1.6)"),
    horsepower: int | None = Query(None, description="Мощность (л.с.)"),
    limit: int = Query(10, ge=1, le=50, description="Макс. количество результатов"),
):
    """Поиск автомобилей по параметрам из справочников. Только активные записи."""
    rows = search_cars_service(
        db, brand=brand, model=model, body_type=body_type, year=year,
        modification=modification, transmission=transmission,
        fuel_type=fuel_type, engine_volume=engine_volume, horsepower=horsepower,
        limit=limit,
    )
    results = [_car_to_result(c) for c in rows]
    return CarSearchResponse(count=len(results), results=results)
