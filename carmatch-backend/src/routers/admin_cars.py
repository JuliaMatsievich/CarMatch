from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import get_db
from src.deps import get_current_admin
from src.models import Car, User
from src.schemas import (
    AdminCarItem,
    AdminCarListResponse,
    AdminCarCreate,
    AdminCarUpdate,
)
from src.services.yandex_embeddings import get_embedding


router = APIRouter(prefix="/admin/cars", tags=["admin-cars"])


def _car_to_admin_item(car: Car) -> AdminCarItem:
    return AdminCarItem(
        id=car.id,
        mark_name=car.mark_name,
        model_name=car.model_name,
        year=car.year,
        price_rub=float(car.price_rub) if car.price_rub is not None else None,
        body_type=car.body_type,
        fuel_type=car.fuel_type,
        engine_volume=float(car.engine_volume) if car.engine_volume is not None else None,
        horsepower=car.horsepower,
        modification=getattr(car, "modification", None) or None,
        transmission=car.transmission,
        country=getattr(car, "country", None) or None,
        images=list(car.images) if car.images else [],
        description=getattr(car, "description", None) or None,
        brand_id=car.brand_id,
        model_id=car.model_id,
        generation_id=car.generation_id,
        modification_id=car.modification_id,
        is_active=car.is_active,
    )


def _build_car_embedding_text(car: Car) -> str:
    parts: list[str] = []
    if car.mark_name:
        parts.append(car.mark_name)
    if car.model_name:
        parts.append(car.model_name)
    if car.year:
        parts.append(f"{car.year} год")
    if car.body_type:
        parts.append(str(car.body_type))
    if car.fuel_type:
        parts.append(str(car.fuel_type))
    if car.transmission:
        parts.append(str(car.transmission))
    if getattr(car, "country", None):
        parts.append(str(car.country))
    if getattr(car, "engine_volume", None):
        parts.append(f"{car.engine_volume} л")
    if getattr(car, "horsepower", None):
        parts.append(f"{car.horsepower} л.с.")
    if getattr(car, "modification", None):
        parts.append(str(car.modification))
    if getattr(car, "description", None):
        parts.append(str(car.description))
    return ", ".join(str(p).strip() for p in parts if str(p).strip())


def _update_car_embedding(db: Session, car: Car) -> None:
    text = _build_car_embedding_text(car)
    if not text:
        car.embedding = None
        db.commit()
        db.refresh(car)
        return

    embedding = get_embedding(text)
    # Если не удалось получить эмбеддинг, не падаем, просто оставляем текущее значение
    if embedding is None:
        return

    car.embedding = embedding
    db.commit()
    db.refresh(car)


@router.get("", response_model=AdminCarListResponse)
def list_cars(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    mark_name: str | None = Query(None),
    model_name: str | None = Query(None),
    body_type: str | None = Query(None),
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
    fuel_type: str | None = Query(None),
    transmission: str | None = Query(None),
    country: str | None = Query(None),
    is_active: bool | None = Query(None),
    sort_by: str | None = Query(None, pattern="^(mark_name|model_name|year)$"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
):
    query = db.query(Car)

    if mark_name:
        query = query.filter(func.lower(Car.mark_name).ilike(f"%{mark_name.lower()}%"))
    if model_name:
        query = query.filter(func.lower(Car.model_name).ilike(f"%{model_name.lower()}%"))
    if body_type:
        query = query.filter(Car.body_type == body_type)
    if year_from is not None:
        query = query.filter(Car.year >= year_from)
    if year_to is not None:
        query = query.filter(Car.year <= year_to)
    if fuel_type:
        query = query.filter(Car.fuel_type == fuel_type)
    if transmission:
        query = query.filter(Car.transmission == transmission)
    if country:
        query = query.filter(Car.country == country)
    if is_active is not None:
        query = query.filter(Car.is_active == is_active)

    total = query.count()
    pages = (total + per_page - 1) // per_page if total else 0

    if sort_by == "mark_name":
        order_column = Car.mark_name
    elif sort_by == "model_name":
        order_column = Car.model_name
    elif sort_by == "year":
        order_column = Car.year
    else:
        order_column = Car.id

    if sort_dir == "desc":
        order_column = order_column.desc()

    items = (
        query.order_by(order_column)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return AdminCarListResponse(
        items=[_car_to_admin_item(c) for c in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{car_id}", response_model=AdminCarItem)
def get_car(
    car_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомобиль не найден",
        )
    return _car_to_admin_item(car)


@router.post("", response_model=AdminCarItem, status_code=status.HTTP_201_CREATED)
def create_car(
    body: AdminCarCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    data = body.model_dump()
    images = data.pop("images", None)
    car = Car(**data)
    if images is not None:
        car.images = images
    db.add(car)
    db.commit()
    db.refresh(car)

    # Обновляем эмбеддинг после сохранения машины
    _update_car_embedding(db, car)

    return _car_to_admin_item(car)


@router.put("/{car_id}", response_model=AdminCarItem)
def update_car(
    car_id: int,
    body: AdminCarUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомобиль не найден",
        )
    data = body.model_dump(exclude_unset=True)
    images = data.pop("images", None)
    for field, value in data.items():
        setattr(car, field, value)
    if images is not None:
        car.images = images
    db.commit()
    db.refresh(car)

    # Пересчитываем эмбеддинг после обновления полей машины
    _update_car_embedding(db, car)

    return _car_to_admin_item(car)


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_car(
    car_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    car = db.query(Car).filter(Car.id == car_id).first()
    if not car:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Автомобиль не найден",
        )
    db.delete(car)
    db.commit()
    return None

