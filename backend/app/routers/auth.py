from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routers.deps import current_user
from app.schemas import CaptchaChallenge, Token, UserOut
from app.utils.captcha import create_captcha, verify_captcha
from app.utils.security import create_access_token, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/captcha", response_model=CaptchaChallenge)
def captcha() -> CaptchaChallenge:
    return CaptchaChallenge(**create_captcha())


@router.post("/login", response_model=Token)
def login(
    username: str = Form(...),
    password: str = Form(...),
    captcha_token: str = Form(...),
    captcha_answer: str = Form(...),
    db: Session = Depends(get_db),
) -> Token:
    if not verify_captcha(captcha_token, captcha_answer):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha javobi noto'g'ri yoki muddati tugagan")
    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    return Token(access_token=create_access_token(user.username))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user
