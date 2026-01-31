from datetime import datetime
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


# --- GigaChat (свободный чат) ---


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatCompleteRequest(BaseModel):
    messages: list[ChatMessage]


class ChatCompleteResponse(BaseModel):
    content: str
