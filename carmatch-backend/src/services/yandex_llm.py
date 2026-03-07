"""
Сервис YandexGPT (Yandex Cloud Foundation Models completion API).
Использует те же учётные данные, что и эмбеддинги: YANDEX_FOLDER_ID, YANDEX_API_KEY.
"""

import logging
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

COMPLETION_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
# yandexgpt-lite — быстрее и дешевле; для Pro: yandexgpt
DEFAULT_MODEL = "yandexgpt-lite/latest"
REQUEST_TIMEOUT = 90.0


def completion(messages: list[dict[str, str]], temperature: float = 0.6, max_tokens: int = 2000) -> str:
    """
    Синхронный вызов YandexGPT completion.
    messages: список {"role": "user" | "assistant" | "system", "content": "..."}.
    Возвращает текст ответа ассистента или пустую строку при ошибке.
    """
    if not (settings.yandex_folder_id and settings.yandex_api_key):
        logger.warning("Yandex LLM: не заданы YANDEX_FOLDER_ID или YANDEX_API_KEY")
        return ""

    # Yandex API ожидает role + text (не content)
    yandex_messages: list[dict[str, str]] = []
    for m in messages:
        role = (m.get("role") or "user").strip().lower()
        if role not in ("system", "user", "assistant"):
            role = "user"
        text = (m.get("content") or m.get("text") or "").strip()
        if not text:
            continue
        yandex_messages.append({"role": role, "text": text})

    if not yandex_messages:
        return ""

    model_uri = f"gpt://{settings.yandex_folder_id}/{DEFAULT_MODEL}"
    payload: dict[str, Any] = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": max_tokens,
        },
        "messages": yandex_messages,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {settings.yandex_api_key}",
        "x-folder-id": settings.yandex_folder_id,
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.post(COMPLETION_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            "Yandex LLM HTTP error: %s %s",
            e.response.status_code,
            (e.response.text or "")[:500],
        )
        return ""
    except Exception as e:
        logger.exception("Yandex LLM request failed: %s", e)
        return ""

    # Синхронный ответ: result.alternatives[0].message.text
    result = data.get("result") or data.get("response")
    if not result:
        logger.error("Yandex LLM: в ответе нет result/response, keys=%s", list(data.keys()))
        return ""

    alternatives = result.get("alternatives")
    if not alternatives or not isinstance(alternatives, list):
        logger.error("Yandex LLM: нет alternatives в result")
        return ""

    first = alternatives[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    text = message.get("text")
    if text is None:
        return ""
    return str(text).strip()
