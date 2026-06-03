from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..deps import get_current_user


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Логин менеджера по логину и паролю (OAuth2 password flow).

    Принимает form-data: `username`, `password`. Возвращает JWT.
    """
    user = db.scalar(
        select(models.AdminUser).where(models.AdminUser.username == form.username)
    )
    if not user or not security.verify_password(form.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = security.create_access_token(subject=user.username)
    return schemas.TokenResponse(access_token=token)


@router.get("/me", response_model=schemas.AdminUserOut)
def me(current: models.AdminUser = Depends(get_current_user)):
    return current
