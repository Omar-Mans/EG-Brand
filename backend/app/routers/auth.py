from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import current_user, is_admin
from ..models import Company, User
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    name: str = Field(default="", max_length=200)
    email: str = Field(min_length=5, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=200)


class LoginIn(BaseModel):
    email: str
    password: str


def _me(user: User, company: Company) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role, "is_admin": is_admin(user),
            "company": {"id": company.id, "name": company.name, "monthly_ai_budget_usd": company.monthly_ai_budget_usd}}


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "الإيميل ده مسجل قبل كده")
    company = Company(name=body.company_name.strip(), monthly_ai_budget_usd=get_settings().default_monthly_ai_budget_usd)
    db.add(company)
    db.flush()
    user = User(company_id=company.id, email=email, name=body.name.strip(), password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return {"token": create_token(user.id), "user": _me(user, company)}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "الإيميل أو كلمة السر غلط")
    return {"token": create_token(user.id), "user": _me(user, db.get(Company, user.company_id))}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _me(user, db.get(Company, user.company_id))
