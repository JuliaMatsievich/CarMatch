from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.deps import get_current_admin
from src.models import Session as SessionModel, ChatMessage, User
from src.schemas import (
    AdminSessionListItem,
    AdminSessionListResponse,
    AdminSessionDetail,
    AdminSessionDetailResponse,
    AdminSessionMessage,
)


router = APIRouter(prefix="/admin/sessions", tags=["admin-sessions"])


def _compute_display_status(session: SessionModel) -> str:
    """
    Простая эвристика статуса сессии для админки.
    """
    if (session.cars_found or 0) > 0:
        return "Успешно"
    if session.status == "error":
        return "Ошибка"
    if session.status == "active":
        return "В процессе"
    return "Завершён"


def _build_params_summary(extracted_params: dict | None) -> str:
    if not extracted_params:
        return ""
    parts: list[str] = []
    for key, value in extracted_params.items():
        if value is None or str(value).strip() == "":
            continue
        parts.append(f"{key}: {value}")
    return ", ".join(parts)


@router.get("", response_model=AdminSessionListResponse)
def list_sessions(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    user_id: int | None = Query(None),
    status_filter: str | None = Query(
        None, alias="status", description="Фильтр по статусу сессии (из поля status)"
    ),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
):
    query = (
        db.query(SessionModel, User)
        .join(User, SessionModel.user_id == User.id)
    )

    if user_id is not None:
        query = query.filter(SessionModel.user_id == user_id)
    if status_filter:
        query = query.filter(SessionModel.status == status_filter)
    if date_from is not None:
        query = query.filter(SessionModel.created_at >= date_from)
    if date_to is not None:
        query = query.filter(SessionModel.created_at <= date_to)

    total = query.count()
    pages = (total + per_page - 1) // per_page if total else 0

    rows = (
        query.order_by(SessionModel.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items: list[AdminSessionListItem] = []
    for session, user in rows:
        display_status = _compute_display_status(session)
        params_summary = _build_params_summary(session.extracted_params or {})
        cars_found = session.cars_found or 0
        items.append(
            AdminSessionListItem(
                id=session.id,
                user_id=session.user_id,
                user_email=user.email,
                created_at=session.created_at,
                message_count=session.message_count,
                display_status=display_status,
                extracted_params_summary=params_summary,
                cars_found=cars_found,
            )
        )

    return AdminSessionListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{session_id}", response_model=AdminSessionDetailResponse)
def get_session_detail(
    session_id: UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    row = (
        db.query(SessionModel, User)
        .join(User, SessionModel.user_id == User.id)
        .filter(SessionModel.id == session_id)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена",
        )
    session, user = row

    display_status = _compute_display_status(session)
    extracted_params = session.extracted_params or {}
    search_results = session.search_results or []
    cars_found = session.cars_found or len(search_results) or 0

    session_schema = AdminSessionDetail(
        id=session.id,
        user_id=session.user_id,
        user_email=user.email,
        status=session.status,
        display_status=display_status,
        extracted_params=extracted_params,
        search_results=search_results,
        created_at=session.created_at,
        message_count=session.message_count,
        cars_found=cars_found,
    )

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.sequence_order)
        .all()
    )
    message_schemas: list[AdminSessionMessage] = []
    for m in messages:
        ai_metadata = getattr(m, "extra_metadata", None)
        message_schemas.append(
            AdminSessionMessage(
                id=m.id,
                role=m.role,
                content=m.content,
                sequence_order=m.sequence_order,
                created_at=m.created_at,
                ai_metadata=ai_metadata,
            )
        )

    return AdminSessionDetailResponse(session=session_schema, messages=message_schemas)


@router.get(
    "/{session_id}/messages",
    response_model=list[AdminSessionMessage],
)
def get_session_messages(
    session_id: UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    exists = (
        db.query(SessionModel.id)
        .filter(SessionModel.id == session_id)
        .first()
    )
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена",
        )

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.sequence_order)
        .all()
    )

    return [
        AdminSessionMessage(
            id=m.id,
            role=m.role,
            content=m.content,
            sequence_order=m.sequence_order,
            created_at=m.created_at,
            ai_metadata=getattr(m, "extra_metadata", None),
        )
        for m in messages
    ]


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_session(
    session_id: UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Удаление чат-сессии и всех её сообщений (каскадно).
    """
    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена",
        )

    db.delete(session)
    db.commit()

