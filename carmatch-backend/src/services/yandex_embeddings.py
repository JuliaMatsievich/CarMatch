"""
Сервис эмбеддингов Yandex Cloud (Foundation Models API).
Используется для заполнения cars.embedding и векторного поиска.
"""
import logging
from typing import List

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

# Модели эмбеддингов (размерность 256)
TEXT_SEARCH_DOC_URI_TEMPLATE = "emb://{folder_id}/text-search-doc/latest"
TEXT_SEARCH_QUERY_URI_TEMPLATE = "emb://{folder_id}/text-search-query/latest"
EMBEDDING_DIMENSION = 256
BASE_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding"


def get_embedding(text: str) -> List[float] | None:
    """
    Возвращает вектор эмбеддинга для текста (модель text-search-doc, размерность 256).
    Если текст пустой или API недоступен — возвращает None.
    """
    if not (settings.yandex_folder_id and settings.yandex_api_key):
        logger.warning("Yandex embeddings: не заданы YANDEX_FOLDER_ID или YANDEX_API_KEY")
        return None
    text = (text or "").strip()
    if not text:
        return None

    model_uri = TEXT_SEARCH_DOC_URI_TEMPLATE.format(folder_id=settings.yandex_folder_id)
    payload = {"modelUri": model_uri, "text": text}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                BASE_URL,
                json=payload,
                headers={"Authorization": f"Api-Key {settings.yandex_api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Yandex embeddings HTTP error: %s %s", e.response.status_code, e.response.text)
        return None
    except Exception as e:
        logger.exception("Yandex embeddings request failed: %s", e)
        return None

    # Ответ: {"embedding": {"embedding": [ ... ]}} или {"embedding": [ ... ]}
    emb = data.get("embedding")
    if emb is None:
        logger.error("Yandex embeddings: в ответе нет поля embedding")
        return None
    if isinstance(emb, dict):
        emb = emb.get("embedding")
    if not isinstance(emb, list) or len(emb) != EMBEDDING_DIMENSION:
        logger.error(
            "Yandex embeddings: неверный формат (ожидается list длины %d), получено %s",
            EMBEDDING_DIMENSION,
            type(emb).__name__ if emb is not None else None,
        )
        return None
    return [float(x) for x in emb]


def get_query_embedding(text: str) -> List[float] | None:
    """
    Возвращает вектор эмбеддинга для поискового запроса (модель text-search-query, размерность 256).
    Используется для векторного поиска: запрос пользователя → эмбеддинг → сравнение с cars.embedding.
    """
    if not (settings.yandex_folder_id and settings.yandex_api_key):
        logger.warning("Yandex embeddings: не заданы YANDEX_FOLDER_ID или YANDEX_API_KEY")
        return None
    text = (text or "").strip()
    if not text:
        return None

    model_uri = TEXT_SEARCH_QUERY_URI_TEMPLATE.format(folder_id=settings.yandex_folder_id)
    payload = {"modelUri": model_uri, "text": text}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                BASE_URL,
                json=payload,
                headers={"Authorization": f"Api-Key {settings.yandex_api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Yandex embeddings HTTP error: %s %s", e.response.status_code, e.response.text)
        return None
    except Exception as e:
        logger.exception("Yandex embeddings request failed: %s", e)
        return None

    emb = data.get("embedding")
    if emb is None:
        logger.error("Yandex embeddings: в ответе нет поля embedding")
        return None
    if isinstance(emb, dict):
        emb = emb.get("embedding")
    if not isinstance(emb, list) or len(emb) != EMBEDDING_DIMENSION:
        logger.error(
            "Yandex embeddings: неверный формат (ожидается list длины %d), получено %s",
            EMBEDDING_DIMENSION,
            type(emb).__name__ if emb is not None else None,
        )
        return None
    return [float(x) for x in emb]
