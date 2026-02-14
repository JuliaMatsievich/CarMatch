"""Роутер для свободного чата с GigaChat (без сессий в БД и поиска машин).

Под капотом используется общий сервис LLM (`deepseek.py`), который сейчас вызывает GigaChat
и применяет те же стилевые промпты, что и логика подбора авто.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from src.deps import get_current_user
from src.models import User
from src.schemas import ChatCompleteRequest, ChatCompleteResponse
from src.services import deepseek as chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/complete", response_model=ChatCompleteResponse)
def chat_complete(
    body: ChatCompleteRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Отправляет историю сообщений в GigaChat и возвращает ответ ассистента.
    Только для авторизованных пользователей. Тематика — свободная (без БД машин).
    """
    try:
        messages = [{"role": m.role, "content": m.content} for m in body.messages]
        # Используем общий сервис LLM с едиными промптами (deepseek.py),
        # который сейчас ходит в GigaChat.
        content = chat_service.chat_complete(messages)
        return ChatCompleteResponse(content=content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка GigaChat: {e!s}",
        )
