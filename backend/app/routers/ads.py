from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, get_brand
from ..models import AdCampaign, SocialAccount, User
from ..security import decrypt
from ..serializers import campaign_out
from ..social import meta

router = APIRouter(prefix="/api/ads", tags=["ads"])


class CampaignIn(BaseModel):
    brand_id: str
    plan: dict


@router.get("/campaigns")
def list_campaigns(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AdCampaign).where(AdCampaign.company_id == user.company_id).order_by(AdCampaign.created_at.desc())).all()
    return [campaign_out(c) for c in rows]


@router.post("/campaigns")
def save_campaign(body: CampaignIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    brand = get_brand(body.brand_id, user, db)
    p = body.plan
    try:
        camp = AdCampaign(company_id=user.company_id, brand_id=brand.id, objective=str(p["objective"]),
                          budget=float(p["budget"]), currency=str(p["currency"]), days=int(p["days"]),
                          platforms=[str(x.get("platform")) for x in p.get("split", [])], plan=p)
    except (KeyError, TypeError, ValueError):
        raise HTTPException(422, "الخطة ناقصة بيانات")
    db.add(camp)
    db.commit()
    return campaign_out(camp)


def _campaign(cid: str, user: User, db: Session) -> AdCampaign:
    c = db.get(AdCampaign, cid)
    if not c or c.company_id != user.company_id:
        raise HTTPException(404, "الحملة مش موجودة")
    return c


@router.post("/campaigns/{campaign_id}/launch")
def launch(campaign_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Creates the campaign in Meta Ads Manager as PAUSED (no spend). Without a Meta ad account it is marked ready."""
    c = _campaign(campaign_id, user, db)
    if c.status == "created_paused":
        raise HTTPException(409, "الحملة اتعملت قبل كده")
    acct = db.scalar(select(SocialAccount).where(SocialAccount.company_id == user.company_id,
                                                 SocialAccount.platform == "meta_ads", SocialAccount.provider == "meta"))
    if not acct:
        c.status = "ready"
        db.commit()
        return campaign_out(c)
    try:
        cid = meta.create_paused_campaign(acct.external_id, decrypt(acct.access_token_enc),
                                          f"EG Brand · {c.objective} · {c.id[:6]}", c.objective)
        c.external_ids, c.status, c.error = {"meta_campaign_id": cid}, "created_paused", ""
    except meta.MetaError as exc:
        c.status, c.error = "failed", str(exc)
    db.commit()
    return campaign_out(c)


@router.get("/campaigns/{campaign_id}/insights")
def insights(campaign_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = _campaign(campaign_id, user, db)
    mid = (c.external_ids or {}).get("meta_campaign_id")
    if not mid:
        return {"available": False}
    acct = db.scalar(select(SocialAccount).where(SocialAccount.company_id == user.company_id, SocialAccount.platform == "meta_ads"))
    if not acct:
        return {"available": False}
    try:
        return {"available": True, "data": meta.campaign_insights(mid, decrypt(acct.access_token_enc))}
    except meta.MetaError as exc:
        raise HTTPException(502, str(exc))
