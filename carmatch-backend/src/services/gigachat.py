"""Сервис для общения с GigaChat API (свободный чат без БД и поиска машин)."""

from __future__ import annotations

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from src.config import settings


def _get_client() -> GigaChat:
    """Создаёт клиент GigaChat с учётом конфига."""
    if not settings.gigachat_credentials:
        raise ValueError("GIGACHAT_CREDENTIALS не заданы")
    return GigaChat(
        credentials=settings.gigachat_credentials,
        verify_ssl_certs=settings.gigachat_verify_ssl_certs,
    )


def chat_complete(messages: list[dict[str, str]]) -> str:
    """
    Отправляет историю сообщений в GigaChat и возвращает ответ ассистента.
    messages: список {"role": "user" | "assistant", "content": "..."}
    """
    if not messages:
        return "Отправьте сообщение, чтобы начать диалог."
    gigachat_messages = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content") or ""
        if role == "user":
            gigachat_messages.append(Messages(role=MessagesRole.USER, content=content))
        elif role == "assistant":
            gigachat_messages.append(
                Messages(role=MessagesRole.ASSISTANT, content=content)
            )
    chat = Chat(messages=gigachat_messages)
    client = _get_client()
    with client:
        response = client.chat(chat)
    if not response.choices:
        return "Пустой ответ от модели."
    return (response.choices[0].message.content or "").strip()
