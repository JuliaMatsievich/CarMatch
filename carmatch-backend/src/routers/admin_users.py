from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import get_db
from src.deps import get_current_admin
from src.models import User, Session as SessionModel
from src.schemas import (
    AdminUserListItem,
    AdminUserListResponse,
    AdminSessionListItem,
    AdminSessionListResponse,
)


router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=AdminUserListResponse)
def list_users(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    email: str | None = Query(
        None, description="Поиск по email (substring, case-insensitive)"
    ),
    is_active: bool | None = Query(None),
):
    base_query = db.query(User)

    if email:
        like = f"%{email.lower()}%"
        base_query = base_query.filter(func.lower(User.email).like(like))
    if is_active is not None:
        base_query = base_query.filter(User.is_active == is_active)

    total = base_query.count()
    pages = (total + per_page - 1) // per_page if total else 0

    users = (
        base_query.order_by(User.id.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # Посчитать количество сессий на пользователя одним запросом
    counts = (
        db.query(SessionModel.user_id, func.count(SessionModel.id))
        .filter(SessionModel.user_id.in_([u.id for u in users]))
        .group_by(SessionModel.user_id)
        .all()
    )
    sessions_count_by_user = {user_id: cnt for user_id, cnt in counts}

    items: list[AdminUserListItem] = []
    for u in users:
        items.append(
            AdminUserListItem(
                id=u.id,
                email=u.email,
                is_active=u.is_active,
                created_at=u.created_at,
                last_login=u.last_login,
                login_count=u.login_count,
                sessions_count=sessions_count_by_user.get(u.id, 0),
            )
        )

    return AdminUserListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/{user_id}/sessions",
    response_model=AdminSessionListResponse,
)
def list_user_sessions(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    query = db.query(SessionModel).filter(SessionModel.user_id == user_id)
    total = query.count()
    pages = (total + per_page - 1) // per_page if total else 0

    sessions = (
        query.order_by(SessionModel.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    from src.routers.admin_sessions import _compute_display_status, _build_params_summary

    items: list[AdminSessionListItem] = []
    for s in sessions:
        display_status = _compute_display_status(s)
        params_summary = _build_params_summary(s.extracted_params or {})
        cars_found = s.cars_found or 0
        items.append(
            AdminSessionListItem(
                id=s.id,
                user_id=s.user_id,
                user_email=user.email,
                created_at=s.created_at,
                message_count=s.message_count,
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


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Удаление пользователя и всех его сессий/сообщений (через ON DELETE CASCADE).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить администратора через этот эндпоинт",
        )

    db.delete(user)
    db.commit()

