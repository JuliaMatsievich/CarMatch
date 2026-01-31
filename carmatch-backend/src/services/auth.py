from datetime import datetime, timedelta
from sqlalchemy.orm import Session

import bcrypt
from jose import JWTError, jwt

from src.config import settings
from src.models import User


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def register(db: Session, email: str, password: str) -> tuple[User, str] | None:
    if get_user_by_email(db, email) is not None:
        return None
    user = User(
        email=email,
        password_hash=hash_password(password),
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.email)
    return user, token


def login(db: Session, email: str, password: str) -> tuple[User, str] | None:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    user.last_login = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.email)
    return user, token
