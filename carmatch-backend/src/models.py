import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    BigInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from src.database import Base


def utcnow():
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_created_at", "created_at"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="active", nullable=False)
    extracted_params = Column(JSONB, default=dict, nullable=False)
    search_criteria = Column(JSONB, default=dict, nullable=False)
    search_results = Column(JSONB, default=list, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    message_count = Column(Integer, default=0, nullable=False)
    parameters_count = Column(Integer, default=0, nullable=False)
    cars_found = Column(Integer, default=0, nullable=False)
    title = Column(String(200), nullable=True)

    __table_args__ = (
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_status", "status"),
        Index("idx_sessions_created_at", "created_at"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    extra_metadata = Column("metadata", JSONB, default=dict, nullable=False)
    sequence_order = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_chat_messages_session_id", "session_id"),
        Index("idx_chat_messages_sequence", "session_id", "sequence_order"),
    )


class CarBrand(Base):
    __tablename__ = "car_brands"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_car_brands_name", "name"),
    )


class CarModel(Base):
    __tablename__ = "car_models"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    brand_id = Column(Integer, ForeignKey("car_brands.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    external_id = Column(String(100), nullable=True)  # The ID from XML
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_car_models_brand", "brand_id"),
        Index("idx_car_models_name", "name"),
        Index("idx_car_models_external_id", "external_id"),
    )


class CarGeneration(Base):
    __tablename__ = "car_generations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("car_models.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=True)  # Generation name if available
    external_id = Column(String(100), nullable=True)  # The ID from XML
    years = Column(JSONB, default=dict, nullable=False)  # Store year ranges as JSON
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_car_generations_model", "model_id"),
        Index("idx_car_generations_external_id", "external_id"),
    )


class CarModification(Base):
    __tablename__ = "car_modifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    generation_id = Column(Integer, ForeignKey("car_generations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)  # Modification name
    external_id = Column(String(100), nullable=True)  # The ID from XML
    body_type = Column(String(100), nullable=True)  # Body type from XML
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_car_modifications_generation", "generation_id"),
        Index("idx_car_modifications_external_id", "external_id"),
    )


class CarComplectation(Base):
    __tablename__ = "car_complectations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    modification_id = Column(Integer, ForeignKey("car_modifications.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # Complectation name
    external_id = Column(String(100), nullable=True)  # The ID from XML
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_car_complectations_modification", "modification_id"),
        Index("idx_car_complectations_external_id", "external_id"),
    )


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source = Column(String(20), default="yandex", nullable=False)
    source_id = Column(String(100), nullable=True)
    mark_name = Column(String(100), nullable=False)
    model_name = Column(String(100), nullable=False)
    body_type = Column(String(50), nullable=True)
    year = Column(Integer, nullable=True)
    price_rub = Column(Numeric(12, 2), nullable=True)
    fuel_type = Column(String(30), nullable=True)
    engine_volume = Column(Numeric(4, 2), nullable=True)
    horsepower = Column(Integer, nullable=True)
    modification = Column(String(100), nullable=True)  # полная строка модификации (например "1.6d MT 90 л.с.")
    transmission = Column(String(20), nullable=True)  # тип коробки: MT, AMT, CVT и т.д.
    specs = Column(JSONB, default=dict, nullable=False)
    images = Column(ARRAY(Text), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    imported_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    
    # Foreign key to connect with normalized reference data
    brand_id = Column(Integer, ForeignKey("car_brands.id", ondelete="SET NULL"), nullable=True, index=True)
    model_id = Column(Integer, ForeignKey("car_models.id", ondelete="SET NULL"), nullable=True, index=True)
    generation_id = Column(Integer, ForeignKey("car_generations.id", ondelete="SET NULL"), nullable=True, index=True)
    modification_id = Column(Integer, ForeignKey("car_modifications.id", ondelete="SET NULL"), nullable=True, index=True)

    __table_args__ = (
        Index("idx_cars_mark_model", "mark_name", "model_name"),
        Index("idx_cars_year", "year"),
        Index("idx_cars_price", "price_rub"),
        Index("idx_cars_body_type", "body_type"),
        Index("idx_cars_fuel_type", "fuel_type"),
        Index("idx_cars_is_active", "is_active", postgresql_where=text("is_active = true")),
        Index("idx_cars_brand", "brand_id"),
        Index("idx_cars_model", "model_id"),
        Index("idx_cars_generation", "generation_id"),
        Index("idx_cars_modification", "modification_id"),
    )


class SearchParameter(Base):
    __tablename__ = "search_parameters"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    param_type = Column(String(50), nullable=False)
    param_value = Column(String(255), nullable=True)
    confidence = Column(Numeric(3, 2), nullable=True)
    message_id = Column(BigInteger, ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (Index("idx_search_parameters_session_id", "session_id"),)
