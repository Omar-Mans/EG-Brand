import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import Brand, User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "سجّل دخول الأول")
    try:
        data = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "الجلسة انتهت، سجّل دخول تاني")
    user = db.get(User, data["sub"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "المستخدم مش موجود")
    return user


def is_admin(user: User) -> bool:
    admins = {e.strip().lower() for e in get_settings().admin_emails.split(",") if e.strip()}
    return user.email.lower() in admins


def get_brand(brand_id: str, user: User, db: Session) -> Brand:
    brand = db.get(Brand, brand_id)
    if not brand or brand.company_id != user.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "البراند مش موجود")
    return brand
