"""Сервис чат-сессий: создание сессии, добавление сообщений, вызов DeepSeek, сохранение в БД."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from src.models import ChatMessage, SearchParameter, Session
from src.services import deepseek as deepseek_service
from src.services.reference_data.car_reference_service import (
    get_body_type_reference,
    search_cars as search_cars_service,
)

MIN_PARAMS_FOR_SEARCH = 3  # поиск в БД при трёх и более параметрах (mark_name, model_name, body_type, year, modification)


def create_session(db: Session, user_id: int) -> Session:
    """Создаёт новую сессию для пользователя."""
    session = Session(
        user_id=user_id,
        status="active",
        extracted_params={},
        search_criteria={},
        search_results=[],
        message_count=0,
        parameters_count=0,
        cars_found=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def add_message(
    db: Session,
    session_id: UUID,
    user_id: int,
    content: str,
) -> tuple[ChatMessage, list[dict], bool]:
    """
    Сохраняет сообщение пользователя. Логика:
    (1) Извлекаем параметры из всей истории диалога (LLM), добавляем к уже накопленным в сессии.
    (2) Если накоплено >= 3 параметров — идём в БД, ищем авто, передаём список в LLM для ответа.
    (3) Если < 3 — LLM задаёт один уточняющий вопрос. Повторяем при каждом новом сообщении, пока не наберётся 3.
    Возвращает (assistant_message, merged_params_dict, ready_for_search, search_results).
    """
    session = db.query(Session).filter(Session.id == session_id, Session.user_id == user_id).first()
    if not session:
        raise ValueError("session_not_found")

    # Сохраняем сообщение пользователя
    max_order = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .count()
    )
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=content,
        sequence_order=max_order + 1,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Заголовок диалога из первого сообщения пользователя
    if max_order == 0 and getattr(session, "title", None) is None:
        title = (content or "").strip()
        if len(title) > 60:
            title = title[:57] + "..."
        if title:
            session.title = title
            db.commit()

    # История для LLM
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.sequence_order)
        .limit(20)
        .all()
    )
    messages = [
        {"role": "user" if m.role == "user" else "assistant", "content": m.content}
        for m in history
    ]

    # Шаг 1: извлечь параметры из всей истории диалога и добавить к уже накопленным в сессии
    try:
        body_type_reference = get_body_type_reference(db)
    except Exception as e:
        logger.exception("get_body_type_reference failed: %s", e)
        body_type_reference = []
    try:
        extracted_params = deepseek_service.extract_params(
            messages,
            current_params=session.extracted_params or {},
            body_type_reference=body_type_reference,
        )
    except Exception as e:
        logger.exception("deepseek extract_params failed: %s", e)
        extracted_params = []

    # Мержим: уже собранные + что вернул LLM + резервное извлечение по ключевым словам (если LLM что-то пропустил)
    allowed_types = (
        "brand", "model", "body_type", "year",
        "modification", "transmission", "fuel_type", "engine_volume", "horsepower",
    )
    merged = dict(session.extracted_params or {})
    for p in extracted_params:
        t = p.get("type")
        val = (p.get("value") or "").strip()
        if not t or not val:
            continue
        # LLM иногда возвращает "mark" вместо "brand" — считаем одним и тем же
        if t == "mark":
            t = "brand"
        if t in allowed_types:
            merged[t] = val
    # Резерв: по ключевым словам из всех сообщений пользователя (топливо, коробка, год, объём, мощность, кузов)
    user_texts = [m.get("content") or "" for m in messages if m.get("role") == "user"]
    fallback = deepseek_service.extract_params_fallback(user_texts, body_type_reference)
    for key, value in fallback.items():
        if key in allowed_types and value and (not merged.get(key) or not str(merged.get(key)).strip()):
            merged[key] = value
            logger.info("extract_params_fallback: added %s=%s (LLM не вернул)", key, value)
    # Исправление: если LLM записал топливо в transmission — переносим в fuel_type и чистим transmission
    _fuel_to_type = (
        ("бензин", "бензин"), ("на бензине", "бензин"), ("бензиновый", "бензин"),
        ("дизель", "дизель"), ("на дизеле", "дизель"), ("дизельный", "дизель"),
        ("гибрид", "гибрид"), ("гибридный", "гибрид"),
        ("электро", "электро"), ("электрический", "электро"),
    )
    tr_val = (merged.get("transmission") or "").strip().lower()
    for fuel_phrase, fuel_norm in _fuel_to_type:
        if fuel_phrase in tr_val or tr_val == fuel_phrase:
            if not merged.get("fuel_type") or not str(merged.get("fuel_type")).strip():
                merged["fuel_type"] = fuel_norm
            merged["transmission"] = ""
            logger.info("extract_params: исправлено — значение «%s» перенесено из transmission в fuel_type", tr_val)
            break
    session.extracted_params = merged
    session.parameters_count = sum(1 for v in merged.values() if v and str(v).strip())
    ready_for_search = session.parameters_count >= MIN_PARAMS_FOR_SEARCH

    # Нормализуем числовые параметры для поиска
    year_for_search = None
    if merged.get("year"):
        try:
            year_for_search = int(str(merged["year"]).strip())
        except (ValueError, TypeError):
            pass
    engine_volume_for_search = None
    if merged.get("engine_volume"):
        try:
            engine_volume_for_search = float(str(merged["engine_volume"]).strip().replace(",", "."))
        except (ValueError, TypeError):
            pass
    horsepower_for_search = None
    if merged.get("horsepower"):
        try:
            horsepower_for_search = int(str(merged["horsepower"]).strip())
        except (ValueError, TypeError):
            pass

    # Шаг 2: поиск в БД (при 3+ параметрах) и генерация ответа
    search_results = []
    if ready_for_search:
        try:
            search_results = search_cars_service(
                db,
                brand=merged.get("brand"),
                model=merged.get("model"),
                body_type=merged.get("body_type"),
                year=year_for_search,
                modification=merged.get("modification"),
                transmission=merged.get("transmission"),
                fuel_type=merged.get("fuel_type"),
                engine_volume=engine_volume_for_search,
                horsepower=horsepower_for_search,
                limit=10,
            )
            logger.info(
                "chat search: merged=%s, params_count=%s, results=%s",
                merged,
                session.parameters_count,
                len(search_results),
            )
        except Exception as e:
            logger.exception("search_cars_service failed: %s", e)
            search_results = []
    # «Критериев достаточно» = набрано 3 параметра (полный поиск); при 0 результатах — детерминированное «не найдено»
    criteria_fulfilled = session.parameters_count >= 3
    try:
        response_text = deepseek_service.generate_response(
            messages,
            params=merged,
            search_results=search_results,
            criteria_fulfilled=criteria_fulfilled,
        )
    except Exception as e:
        logger.exception("deepseek generate_response failed: %s", e)
        response_text = "Не удалось обработать запрос. Попробуйте ещё раз."

    # Сохраняем ответ ассистента
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=response_text,
        sequence_order=max_order + 2,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    # Записываем search_parameters
    for p in extracted_params:
        sp = SearchParameter(
            session_id=session_id,
            param_type=p.get("type", ""),
            param_value=p.get("value", ""),
            confidence=p.get("confidence"),
            message_id=assistant_msg.id,
        )
        db.add(sp)
    session.message_count = max_order + 2
    db.commit()
    db.refresh(session)

    # Возвращаем накопленные параметры (merged), а не только что извлечённые из последнего сообщения
    return assistant_msg, merged, ready_for_search, search_results
