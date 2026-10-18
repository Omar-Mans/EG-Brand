"""AI cost per company: what was spent, and unit economics for pricing."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user, is_admin
from ..models import Company, UsageEvent, User
from ..serializers import iso

router = APIRouter(prefix="/api/usage", tags=["usage"])

# Used until the company has real calls for a feature.
DEFAULT_CALL = {"dna": (1200, 1400), "calendar": (1500, 4500), "regen": (500, 250), "ads": (700, 1100)}


class EconomicsIn(BaseModel):
    in_per_m: float = Field(default=3.0, ge=0)
    out_per_m: float = Field(default=15.0, ge=0)
    image_cost: float = Field(default=0.04, ge=0)
    images_per_month: int = Field(default=0, ge=0)
    regens_per_month: int = Field(default=20, ge=0)
    ads_plans_per_month: int = Field(default=1, ge=0)
    fee_pct: float = Field(default=3.0, ge=0, le=50)
    price_egp: float = Field(default=225, ge=0)
    price_sar: float = Field(default=74, ge=0)
    fx_egp: float = Field(default=48, gt=0)
    fx_sar: float = Field(default=3.75, gt=0)
    use_measured_cost: bool = True  # use the real recorded cost per call when available


def _month_start() -> datetime:
    return datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _summary(db: Session, company_id: str) -> dict:
    start = _month_start()
    rows = db.execute(select(UsageEvent.feature, func.count(), func.sum(UsageEvent.input_tokens),
                             func.sum(UsageEvent.output_tokens), func.sum(UsageEvent.cost_usd))
                      .where(UsageEvent.company_id == company_id, UsageEvent.created_at >= start)
                      .group_by(UsageEvent.feature)).all()
    by_feature = [{"feature": f, "calls": n, "input_tokens": int(i or 0), "output_tokens": int(o or 0), "cost_usd": float(c or 0)}
                  for f, n, i, o, c in rows]
    company = db.get(Company, company_id)
    spent = sum(x["cost_usd"] for x in by_feature)
    return {"company_id": company_id, "company_name": company.name if company else "", "month_start": iso(start),
            "spent_usd": spent, "budget_usd": company.monthly_ai_budget_usd if company else 0,
            "calls": sum(x["calls"] for x in by_feature), "by_feature": by_feature}


@router.get("/summary")
def summary(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _summary(db, user.company_id)


@router.get("/events")
def events(limit: int = 50, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(UsageEvent).where(UsageEvent.company_id == user.company_id)
                      .order_by(UsageEvent.created_at.desc()).limit(min(limit, 200))).all()
    return [{"id": e.id, "feature": e.feature, "model": e.model, "input_tokens": e.input_tokens, "output_tokens": e.output_tokens,
             "cost_usd": e.cost_usd, "latency_ms": e.latency_ms, "ok": e.ok, "created_at": iso(e.created_at)} for e in rows]


@router.post("/economics")
def economics(body: EconomicsIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    per_call = {}
    for feature, (di, do) in DEFAULT_CALL.items():
        row = db.execute(select(func.count(), func.avg(UsageEvent.input_tokens), func.avg(UsageEvent.output_tokens),
                                func.avg(UsageEvent.cost_usd))
                         .where(UsageEvent.feature == feature, UsageEvent.ok.is_(True), UsageEvent.model != "mock")).one()
        n, ai, ao, ac = row
        measured = bool(n)
        i, o = (float(ai), float(ao)) if measured else (di, do)
        cost = float(ac) if measured and body.use_measured_cost and ac else i / 1e6 * body.in_per_m + o / 1e6 * body.out_per_m
        per_call[feature] = {"input_tokens": round(i), "output_tokens": round(o), "cost_usd": cost, "measured_calls": n}
    setup = per_call["dna"]["cost_usd"]
    monthly_ai = per_call["calendar"]["cost_usd"] + per_call["regen"]["cost_usd"] * body.regens_per_month \
        + per_call["ads"]["cost_usd"] * body.ads_plans_per_month
    monthly_images = body.image_cost * body.images_per_month
    monthly = monthly_ai + monthly_images
    markets = []
    for key, price, fx, cur in (("EG", body.price_egp, body.fx_egp, "EGP"), ("SA", body.price_sar, body.fx_sar, "SAR")):
        usd = price / fx
        fee = usd * body.fee_pct / 100
        gross = usd - fee - monthly
        markets.append({"market": key, "price": price, "currency": cur, "price_usd": usd, "payment_fee_usd": fee,
                        "ai_cost_usd": monthly, "gross_profit_usd": gross, "gross_margin_pct": (gross / usd * 100) if usd else 0})
    return {"per_call": per_call, "setup_cost_usd": setup, "monthly_ai_usd": monthly_ai,
            "monthly_images_usd": monthly_images, "monthly_cost_usd": monthly, "markets": markets}


@router.get("/admin/companies")
def all_companies(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not is_admin(user):
        raise HTTPException(403, "الصفحة دي للأدمن بس")
    return [_summary(db, c.id) for c in db.scalars(select(Company)).all()]
