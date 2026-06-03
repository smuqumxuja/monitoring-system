from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.rbac import require_admin_role
from app.utils.security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_user_from_token(db: Session, token: str) -> User | None:
    username = decode_access_token(token)
    if not username:
        return None
    return db.query(User).filter(User.username == username, User.is_active.is_(True)).first()


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user = get_user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    require_admin_role(user)
    return user
