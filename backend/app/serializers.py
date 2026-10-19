from .models import AdCampaign, Brand, Job, Post, SocialAccount


def iso(dt):
    return dt.isoformat() if dt else None


def brand_out(b: Brand) -> dict:
    return {"id": b.id, "name": b.name, "brief": b.brief or {}, "dna": b.dna,
            "discovery": b.discovery or {}, "strategy": b.strategy,
            "created_at": iso(b.created_at), "updated_at": iso(b.updated_at)}


def post_out(p: Post) -> dict:
    return {"id": p.id, "brand_id": p.brand_id, "month": p.month, "day": p.day, "time": p.time, "format": p.format,
            "pillar": p.pillar, "occasion": p.occasion, "headline": p.headline, "caption": p.caption,
            "hashtags": p.hashtags or [], "cta": p.cta, "template": p.template, "approved": p.approved,
            "design": p.design or {}, "bg_url": p.bg_url, "metrics": p.metrics or {}, "metrics_at": iso(p.metrics_at),
            "image_url": p.image_url, "status": p.status, "scheduled_at": iso(p.scheduled_at),
            "platforms": p.platforms or [], "publish_results": p.publish_results or {}, "error": p.error}


def account_out(a: SocialAccount) -> dict:
    return {"id": a.id, "provider": a.provider, "platform": a.platform, "external_id": a.external_id,
            "name": a.name, "created_at": iso(a.created_at)}


def campaign_out(c: AdCampaign) -> dict:
    return {"id": c.id, "brand_id": c.brand_id, "objective": c.objective, "budget": c.budget, "currency": c.currency,
            "days": c.days, "platforms": c.platforms or [], "plan": c.plan or {}, "status": c.status,
            "external_ids": c.external_ids or {}, "error": c.error, "created_at": iso(c.created_at)}


def job_out(j: Job) -> dict:
    return {"id": j.id, "kind": j.kind, "status": j.status, "result": j.result, "error": j.error,
            "created_at": iso(j.created_at), "finished_at": iso(j.finished_at)}
