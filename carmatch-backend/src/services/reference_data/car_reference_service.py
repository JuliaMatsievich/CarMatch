from sqlalchemy import distinct, or_
from sqlalchemy.orm import Session
from typing import List, Optional

from src.models import Car, CarBrand, CarModel, CarGeneration, CarModification, CarComplectation

# Нормализация типа коробки из формулировок пользователя/LLM к подстроке для поиска в БД (MT, AT, AMT, CVT)
TRANSMISSION_SEARCH_ALIASES = {
    "автомат": "AT",
    "автоматическая": "AT",
    "акпп": "AT",
    "механика": "MT",
    "механическая": "MT",
    "мкпп": "MT",
    "ручная": "MT",
    "вариатор": "CVT",
    "робот": "AMT",
    "роботизированная": "AMT",
}


def _normalize_transmission_for_search(transmission: Optional[str]) -> Optional[str]:
    """Для поиска в БД: «автомат» -> AT (ILIKE %AT% найдёт AT, AMT), «механика» -> MT и т.д."""
    if not transmission or not transmission.strip():
        return None
    s = transmission.strip().lower()
    return TRANSMISSION_SEARCH_ALIASES.get(s) or s


def get_all_brands(db: Session) -> List[CarBrand]:
    """Get all car brands from the database."""
    return db.query(CarBrand).all()


def get_brand_by_name(db: Session, name: str) -> Optional[CarBrand]:
    """Get a car brand by its name."""
    return db.query(CarBrand).filter(CarBrand.name == name).first()


def get_models_by_brand(db: Session, brand_id: int) -> List[CarModel]:
    """Get all models for a specific brand."""
    return db.query(CarModel).filter(CarModel.brand_id == brand_id).all()


def get_generations_by_model(db: Session, model_id: int) -> List[CarGeneration]:
    """Get all generations for a specific model."""
    return db.query(CarGeneration).filter(CarGeneration.model_id == model_id).all()


def get_modifications_by_generation(db: Session, generation_id: int) -> List[CarModification]:
    """Get all modifications for a specific generation."""
    return db.query(CarModification).filter(CarModification.generation_id == generation_id).all()


def get_complectations_by_modification(db: Session, modification_id: int) -> List[CarComplectation]:
    """Get all complectations for a specific modification."""
    return db.query(CarComplectation).filter(CarComplectation.modification_id == modification_id).all()


def get_model_by_name_and_brand(db: Session, brand_id: int, name: str) -> Optional[CarModel]:
    """Get a model by its name and brand ID."""
    return db.query(CarModel).filter(
        CarModel.brand_id == brand_id,
        CarModel.name == name
    ).first()


def get_generation_by_external_id(db: Session, external_id: str) -> Optional[CarGeneration]:
    """Get a generation by its external ID."""
    return db.query(CarGeneration).filter(CarGeneration.external_id == external_id).first()


def get_modification_by_external_id(db: Session, external_id: str) -> Optional[CarModification]:
    """Get a modification by its external ID."""
    return db.query(CarModification).filter(CarModification.external_id == external_id).first()


def get_complectation_by_external_id(db: Session, external_id: str) -> Optional[CarComplectation]:
    """Get a complectation by its external ID."""
    return db.query(CarComplectation).filter(CarComplectation.external_id == external_id).first()


def get_body_type_reference(db: Session) -> List[str]:
    """Уникальные body_type из таблицы cars — чтобы LLM предлагал только то, что есть в базе авто."""
    rows = (
        db.query(distinct(Car.body_type))
        .filter(Car.body_type.isnot(None), Car.body_type != "")
        .all()
    )
    return [r[0].strip() for r in rows if r[0] and r[0].strip()]


# Пары (кириллица, латиница) для поиска типа кузова: в БД может быть и то и другое
BODY_TYPE_SEARCH_PAIRS = [
    ("хэтчбек", "hatchback"),
    ("седан", "sedan"),
    ("универсал", "wagon"),
    ("внедорожник", "suv"),
    ("кроссовер", "crossover"),
    ("купе", "coupe"),
    ("минивэн", "minivan"),
    ("лифтбек", "liftback"),
    ("кабриолет", "cabriolet"),
    ("пикап", "pickup"),
]

# Варианты написания (е/э и т.д.): как может прийти от пользователя/LLM -> каноническая подстрока для БД
BODY_TYPE_NORMALIZE = {
    "хетчбек": "хэтчбек",   # в БД: «Хэтчбек 3 дв.» — с «э»
    "хэтчбек": "хэтчбек",
    "седан": "седан",
    "универсал": "универсал",
    "внедорожник": "внедорожник",
    "кроссовер": "кроссовер",
    "купе": "купе",
    "минивен": "минивэн",
    "минивэн": "минивэн",
    "лифтбек": "лифтбек",
    "кабриолет": "кабриолет",
    "пикап": "пикап",
}


def _body_type_filter_condition(body_type: Optional[str]):
    """Для поиска: «Хэтчбек»/«Hatchback»/«хетчбек» (е) -> OR по кириллице и латинице в Car.body_type."""
    if not body_type or not body_type.strip():
        return None
    s = body_type.strip().lower()
    # Нормализуем е/э и др.: «хетчбек» -> «хэтчбек», чтобы совпало с БД
    search_term = BODY_TYPE_NORMALIZE.get(s, s)
    for cyr, lat in BODY_TYPE_SEARCH_PAIRS:
        if search_term == cyr or s == lat or (cyr in search_term) or (cyr in s) or (lat in s):
            return or_(
                Car.body_type.ilike(f"%{cyr}%"),
                Car.body_type.ilike(f"%{lat}%"),
            )
    return Car.body_type.ilike(f"%{search_term}%")


# Алиасы марки для поиска: как пользователь мог написать -> имя в БД
BRAND_SEARCH_ALIASES = {
    "рено": "Renault",
    "шкода": "Škoda",
    "бмв": "BMW",
    "мерседес": "Mercedes-Benz",
    "мерс": "Mercedes-Benz",
    "тойота": "Toyota",
    "хёндай": "Hyundai",
    "киа": "Kia",
    "лада": "Lada",
    "вольксваген": "Volkswagen",
    "фольксваген": "Volkswagen",
    "ву": "Volkswagen",
    "ниссан": "Nissan",
}


def get_brand_by_name_ilike(db: Session, name: str) -> Optional[CarBrand]:
    """Find brand by name (case-insensitive, trimmed). Учитывает алиасы (рено -> Renault)."""
    if not name or not name.strip():
        return None
    search = name.strip()
    canonical = BRAND_SEARCH_ALIASES.get(search.lower())
    if canonical:
        search = canonical
    return db.query(CarBrand).filter(CarBrand.name.ilike(search)).first()


def get_model_by_name_ilike(db: Session, name: str, brand_id: Optional[int] = None) -> Optional[CarModel]:
    """Find model by name (case-insensitive); optionally scoped by brand_id."""
    if not name or not name.strip():
        return None
    search = name.strip()
    q = db.query(CarModel).filter(CarModel.name.ilike(search))
    if brand_id is not None:
        q = q.filter(CarModel.brand_id == brand_id)
    return q.first()


def search_cars(
    db: Session,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    body_type: Optional[str] = None,
    year: Optional[int] = None,
    modification: Optional[str] = None,
    transmission: Optional[str] = None,
    fuel_type: Optional[str] = None,
    engine_volume: Optional[float] = None,
    horsepower: Optional[int] = None,
    limit: int = 10,
) -> List[Car]:
    """
    Search cars via reference tables: brand/model by text lookup, body_type by exact match,
    year by exact match, modification by substring (ILIKE), transmission (gearbox) by ILIKE,
    fuel_type by ILIKE, engine_volume and horsepower by exact match.
    Returns active cars only, ordered by price (asc, nulls last).
    """
    q = db.query(Car).filter(Car.is_active.is_(True))
    brand_id: Optional[int] = None
    model_id: Optional[int] = None
    brand_name_for_fallback: Optional[str] = None

    if brand and brand.strip():
        b = get_brand_by_name_ilike(db, brand)
        if b:
            brand_id = b.id
            brand_name_for_fallback = b.name
            q = q.filter(Car.brand_id == brand_id)
        else:
            return []
    if model and model.strip():
        # Не фильтровать по модели, если LLM подставил марку в поле модели (напр. model="Renault" при brand="Renault")
        if brand_name_for_fallback and model.strip().lower() == brand_name_for_fallback.strip().lower():
            pass  # не добавляем фильтр по модели
        else:
            m = get_model_by_name_ilike(db, model, brand_id)
            if m:
                model_id = m.id
                q = q.filter(Car.model_id == model_id)
            else:
                # Модель не найдена в справочнике (напр. "Clio" при записях "Clio, V") — фильтр по подстроке model_name
                q = q.filter(Car.model_name.ilike(f"%{model.strip()}%"))
    if body_type and body_type.strip():
        bt_cond = _body_type_filter_condition(body_type)
        if bt_cond is not None:
            q = q.filter(bt_cond)
    if year is not None:
        q = q.filter(Car.year == year)
    if modification and modification.strip():
        mod = modification.strip()
        q = q.filter(Car.modification.ilike(f"%{mod}%"))
    if transmission and transmission.strip():
        tr = _normalize_transmission_for_search(transmission) or transmission.strip()
        q = q.filter(Car.transmission.ilike(f"%{tr}%"))
    if fuel_type and fuel_type.strip():
        ft = fuel_type.strip()
        q = q.filter(Car.fuel_type.ilike(f"%{ft}%"))
    if engine_volume is not None:
        q = q.filter(Car.engine_volume == engine_volume)
    if horsepower is not None:
        q = q.filter(Car.horsepower == horsepower)

    q = q.order_by(Car.price_rub.asc().nullslast())
    rows = q.limit(limit).all()
    # Резерв: если по brand_id ничего не нашли, но бренд в справочнике есть — ищем по mark_name
    # (у части записей cars brand_id мог не заполняться при импорте)
    if not rows and brand_name_for_fallback and brand_name_for_fallback.strip():
        q2 = db.query(Car).filter(Car.is_active.is_(True))
        q2 = q2.filter(Car.mark_name.ilike(brand_name_for_fallback.strip()))
        if model and model.strip() and model.strip().lower() != brand_name_for_fallback.strip().lower():
            q2 = q2.filter(Car.model_name.ilike(f"%{model.strip()}%"))
        if body_type and body_type.strip():
            bt_cond = _body_type_filter_condition(body_type)
            if bt_cond is not None:
                q2 = q2.filter(bt_cond)
        if year is not None:
            q2 = q2.filter(Car.year == year)
        if modification and modification.strip():
            q2 = q2.filter(Car.modification.ilike(f"%{modification.strip()}%"))
        if transmission and transmission.strip():
            tr = _normalize_transmission_for_search(transmission) or transmission.strip()
            q2 = q2.filter(Car.transmission.ilike(f"%{tr}%"))
        if fuel_type and fuel_type.strip():
            q2 = q2.filter(Car.fuel_type.ilike(f"%{fuel_type.strip()}%"))
        if engine_volume is not None:
            q2 = q2.filter(Car.engine_volume == engine_volume)
        if horsepower is not None:
            q2 = q2.filter(Car.horsepower == horsepower)
        q2 = q2.order_by(Car.price_rub.asc().nullslast())
        rows = q2.limit(limit).all()
    return rows