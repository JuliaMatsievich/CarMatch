"""Роутер чат-сессий: создание сессии, отправка и получение сообщений."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.deps import get_current_user
from src.models import ChatMessage, User
from src.schemas import (
    ChatSessionListItem,
    ChatSessionResponse,
    MessageCreate,
    MessageListItem,
    MessageResponse,
    MessagesListResponse,
    ExtractedParam,
    CarResult,
)
from src.database import get_db
from src.services.chat import add_message, create_session

router = APIRouter(prefix="/chat", tags=["chat"])


def _car_to_result(car) -> CarResult:
    """Преобразует ORM Car в схему CarResult для ответа (все поля из БД)."""
    return CarResult(
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
        images=list(car.images) if car.images else [],
        description=getattr(car, "description", None) or None,
        brand_id=car.brand_id,
        model_id=car.model_id,
        generation_id=car.generation_id,
        modification_id=car.modification_id,
    )


@router.post("/sessions", response_model=ChatSessionResponse)
def post_create_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Создать новую сессию чата."""
    session = create_session(db, current_user.id)
    return ChatSessionResponse(
        id=session.id,
        user_id=session.user_id,
        status=session.status,
        extracted_params=session.extracted_params or {},
        search_results=session.search_results or [],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions/current", response_model=ChatSessionResponse)
def get_current_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Текущий «новый диалог»: пустая сессия (message_count=0) для пользователя.
    Если есть — возвращаем последнюю по updated_at; если нет — создаём новую.
    При следующем заходе пользователь остаётся в этой же сессии, пока не нажмёт «Новый диалог».
    """
    from src.models import Session as SessionModel

    empty = (
        db.query(SessionModel)
        .filter(
            SessionModel.user_id == current_user.id,
            SessionModel.message_count == 0,
        )
        .order_by(SessionModel.updated_at.desc())
        .first()
    )
    if empty:
        return ChatSessionResponse(
            id=empty.id,
            user_id=empty.user_id,
            status=empty.status,
            extracted_params=empty.extracted_params or {},
            search_results=empty.search_results or [],
            created_at=empty.created_at,
            updated_at=empty.updated_at,
        )
    session = create_session(db, current_user.id)
    return ChatSessionResponse(
        id=session.id,
        user_id=session.user_id,
        status=session.status,
        extracted_params=session.extracted_params or {},
        search_results=session.search_results or [],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions")
def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Список сессий текущего пользователя (по updated_at DESC)."""
    from src.models import Session as SessionModel

    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == current_user.id)
        .order_by(SessionModel.updated_at.desc())
        .all()
    )
    return {
        "sessions": [
            ChatSessionListItem(
                id=s.id,
                status=s.status,
                title=getattr(s, "title", None),
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=s.message_count,
            )
            for s in sessions
        ]
    }


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
def post_message(
    session_id: UUID,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отправить сообщение в сессию; вернуть ответ с накопленными extracted_params, ready_for_search и search_results."""
    try:
        assistant_msg, merged_params, ready_for_search, search_results = add_message(
            db, session_id, current_user.id, body.content.strip()
        )
    except ValueError as e:
        if str(e) == "session_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сессия не найдена или доступ запрещён",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    # Накопленные за весь диалог параметры (не только из последнего сообщения)
    params = [
        ExtractedParam(type=k, value=v, confidence=0.9)
        for k, v in (merged_params or {}).items()
        if v and str(v).strip()
    ]
    car_results = [_car_to_result(c) for c in search_results]
    return MessageResponse(
        id=assistant_msg.id,
        session_id=assistant_msg.session_id,
        role=assistant_msg.role,
        content=assistant_msg.content,
        sequence_order=assistant_msg.sequence_order,
        created_at=assistant_msg.created_at,
        extracted_params=params,
        ready_for_search=ready_for_search,
        search_results=car_results,
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Удалить диалог (сессию) текущего пользователя. Сообщения удаляются каскадно."""
    from src.models import Session as SessionModel

    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id, SessionModel.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена или доступ запрещён",
        )
    db.delete(session)
    db.commit()
    return None


@router.get("/sessions/{session_id}/messages", response_model=MessagesListResponse)
def get_messages(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить историю сообщений сессии."""
    from src.models import Session as SessionModel

    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id, SessionModel.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена или доступ запрещён",
        )
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.sequence_order)
        .all()
    )
    return MessagesListResponse(
        messages=[
            MessageListItem(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                sequence_order=m.sequence_order,
                created_at=m.created_at,
            )
            for m in messages
        ]
    )
