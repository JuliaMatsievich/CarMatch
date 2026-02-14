from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Пароль должен содержать минимум 8 символов")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Пароль должен содержать минимум 8 символов")


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- DeepSeek (свободный чат, без сессий) ---


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatCompleteRequest(BaseModel):
    messages: list[ChatMessage]


class ChatCompleteResponse(BaseModel):
    content: str


# --- Чат-сессии и подбор авто ---


class ChatSessionResponse(BaseModel):
    id: UUID
    user_id: int
    status: str
    extracted_params: dict
    search_results: list
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatSessionListItem(BaseModel):
    id: UUID
    status: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Текст сообщения не должен быть пустым")


class ExtractedParam(BaseModel):
    type: str
    value: str
    confidence: float


class MessageListItem(BaseModel):
    id: int
    session_id: UUID
    role: str
    content: str
    sequence_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    session_id: UUID
    role: str
    content: str
    sequence_order: int
    created_at: datetime
    extracted_params: list[ExtractedParam] = []
    ready_for_search: bool = False
    search_results: list["CarResult"] = []  # автомобили из БД по результатам поиска


class MessagesListResponse(BaseModel):
    messages: list[MessageListItem]


# --- Справочные данные автомобилей ---


class CarBrandBase(BaseModel):
    name: str
    code: str | None = None


class CarBrandCreate(CarBrandBase):
    pass


class CarBrandResponse(CarBrandBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CarModelBase(BaseModel):
    brand_id: int
    name: str
    external_id: str | None = None


class CarModelCreate(CarModelBase):
    pass


class CarModelResponse(CarModelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CarGenerationBase(BaseModel):
    model_id: int
    name: str | None = None
    external_id: str | None = None
    years: dict = {}


class CarGenerationCreate(CarGenerationBase):
    pass


class CarGenerationResponse(CarGenerationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CarModificationBase(BaseModel):
    generation_id: int
    name: str
    external_id: str | None = None
    body_type: str | None = None


class CarModificationCreate(CarModificationBase):
    pass


class CarModificationResponse(CarModificationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CarComplectationBase(BaseModel):
    modification_id: int
    name: str
    external_id: str | None = None


class CarComplectationCreate(CarComplectationBase):
    pass


class CarComplectationResponse(CarComplectationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Поиск автомобилей ---


class CarResult(BaseModel):
    id: int
    mark_name: str
    model_name: str
    year: int | None
    price_rub: float | None
    body_type: str | None
    fuel_type: str | None
    engine_volume: float | None = None
    horsepower: int | None = None
    modification: str | None = None  # полная строка модификации
    transmission: str | None = None  # тип коробки (MT, AMT, CVT и т.д.)
    images: list[str] = []
    description: str | None = None
    brand_id: int | None = None
    model_id: int | None = None
    generation_id: int | None = None
    modification_id: int | None = None

    class Config:
        from_attributes = True


class CarSearchResponse(BaseModel):
    count: int
    results: list[CarResult]


# Разрешить forward reference в MessageResponse.search_results
MessageResponse.model_rebuild()
