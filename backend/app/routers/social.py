import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import current_user
from ..models import SocialAccount, User
from ..security import create_token, decode_token, encrypt
from ..serializers import account_out
from ..social import meta

router = APIRouter(prefix="/api/social", tags=["social"])
PLATFORMS = ["instagram", "facebook", "tiktok", "snapchat", "x"]


class MockConnectIn(BaseModel):
    platform: str


@router.get("/status")
def status():
    s = get_settings()
    return {"live": s.social_live, "meta_configured": bool(s.meta_app_id and s.meta_app_secret),
            "platforms": PLATFORMS, "live_platforms": sorted(["facebook", "instagram"])}


@router.get("/accounts")
def accounts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(SocialAccount).where(SocialAccount.company_id == user.company_id)).all()
    return [account_out(a) for a in rows]


@router.delete("/accounts/{account_id}")
def disconnect(account_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    acct = db.get(SocialAccount, account_id)
    if not acct or acct.company_id != user.company_id:
        raise HTTPException(404, "الحساب مش موجود")
    db.delete(acct)
    db.commit()
    return {"ok": True}


@router.post("/mock/connect")
def mock_connect(body: MockConnectIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if get_settings().social_live:
        raise HTTPException(409, "الربط التجريبي مقفول في وضع النشر الحقيقي")
    if body.platform not in PLATFORMS:
        raise HTTPException(422, "منصة غير معروفة")
    db.execute(delete(SocialAccount).where(SocialAccount.company_id == user.company_id, SocialAccount.platform == body.platform))
    acct = SocialAccount(company_id=user.company_id, provider="mock", platform=body.platform,
                         external_id=f"mock-{body.platform}", name=f"حساب تجريبي ({body.platform})")
    db.add(acct)
    db.commit()
    return account_out(acct)


@router.get("/meta/login-url")
def meta_login_url(user: User = Depends(current_user)):
    s = get_settings()
    if not (s.meta_app_id and s.meta_app_secret):
        raise HTTPException(409, "تطبيق Meta مش متظبط (META_APP_ID و META_APP_SECRET)")
    state = create_token(user.id, purpose="meta_oauth", minutes=15, extra={"company_id": user.company_id})
    return {"url": meta.login_url(state)}


@router.get("/meta/callback")
def meta_callback(code: str = "", state: str = "", error: str = "", db: Session = Depends(get_db)):
    front = get_settings().frontend_url.rstrip("/")
    if error or not code:
        return RedirectResponse(f"{front}/settings?meta=cancelled")
    try:
        data = decode_token(state, purpose="meta_oauth")
    except jwt.PyJWTError:
        return RedirectResponse(f"{front}/settings?meta=expired")
    company_id = data["company_id"]
    try:
        token = meta.exchange_code(code)
        assets = meta.list_assets(token)
    except meta.MetaError as exc:
        return RedirectResponse(f"{front}/settings?meta=error&reason={str(exc)[:120]}")
    # One connection per platform per company in the MVP: the first page with Instagram wins.
    pages = sorted(assets["pages"], key=lambda p: 0 if p.get("instagram_business_account") else 1)
    db.execute(delete(SocialAccount).where(SocialAccount.company_id == company_id,
                                           SocialAccount.platform.in_(["facebook", "instagram", "meta_ads"])))
    if pages:
        page = pages[0]
        db.add(SocialAccount(company_id=company_id, provider="meta", platform="facebook", external_id=page["id"],
                             name=page.get("name", ""), access_token_enc=encrypt(page["access_token"])))
        ig = page.get("instagram_business_account")
        if ig:
            db.add(SocialAccount(company_id=company_id, provider="meta", platform="instagram", external_id=ig["id"],
                                 name=ig.get("username", ""), access_token_enc=encrypt(page["access_token"])))
    if assets["ad_accounts"]:
        ad = assets["ad_accounts"][0]
        db.add(SocialAccount(company_id=company_id, provider="meta", platform="meta_ads", external_id=ad["id"],
                             name=ad.get("name", ""), access_token_enc=encrypt(token), extra={"currency": ad.get("currency")}))
    db.commit()
    return RedirectResponse(f"{front}/settings?meta=connected")
