"""Background jobs (AI generation) and the publishing scheduler. Run by worker.py or inside the API in dev."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .ai import images, services
from .ai.llm import AIError
from .db import SessionLocal, is_postgres
from .models import Brand, Job, Post
from .social.publisher import publish_post

log = logging.getLogger(__name__)
MAX_PUBLISH_ATTEMPTS = 3


def enqueue(db: Session, company_id: str, kind: str, payload: dict) -> Job:
    job = Job(company_id=company_id, kind=kind, payload=payload)
    db.add(job)
    db.commit()
    return job


def _brand(db: Session, job: Job) -> Brand:
    brand = db.get(Brand, job.payload["brand_id"])
    if not brand or brand.company_id != job.company_id:
        raise AIError("not_found", "البراند مش موجود")
    return brand


def run_job(db: Session, job: Job) -> dict:
    p = job.payload
    if job.kind == "dna":
        return {"dna": services.generate_dna(db, _brand(db, job))}
    if job.kind == "calendar":
        posts = services.generate_calendar(db, _brand(db, job), int(p["year"]), int(p["month"]), int(p.get("count", 12)))
        return {"post_ids": [x.id for x in posts]}
    if job.kind == "regen":
        post = db.get(Post, p["post_id"])
        if not post or post.company_id != job.company_id:
            raise AIError("not_found", "البوست مش موجود")
        services.rewrite_post(db, _brand(db, job), post, p.get("instruction", ""))
        return {"post_id": post.id}
    if job.kind == "agent":
        return services.run_agent(db, _brand(db, job), p.get("command", ""))
    if job.kind == "images":
        brand = _brand(db, job)
        q = select(Post).where(Post.brand_id == brand.id, Post.status == "draft")
        if p.get("month"):
            q = q.where(Post.month == p["month"])
        if p.get("post_ids"):
            q = q.where(Post.id.in_(p["post_ids"]))
        done, failed = [], 0
        for post in db.scalars(q.order_by(Post.day)).all()[:20]:
            if post.bg_url and not p.get("replace"):
                continue
            try:
                images.generate_background(db, brand, post)
                done.append(post.id)
            except AIError as exc:
                if exc.code == "budget_exceeded":
                    raise
                failed += 1
        if failed and not done:
            raise AIError("image_failed", "مزود الصور مش متاح دلوقتي")
        return {"post_ids": done, "failed": failed}
    if job.kind == "background":
        post = db.get(Post, p["post_id"])
        if not post or post.company_id != job.company_id:
            raise AIError("not_found", "البوست مش موجود")
        return {"post_id": post.id, "bg_url": images.generate_background(db, _brand(db, job), post, p.get("prompt", ""))}
    if job.kind == "ads":
        return {"plan": services.plan_ads(db, _brand(db, job), p["objective"], float(p["budget"]), int(p["days"]), p.get("platforms", []))}
    raise AIError("unknown_job", f"نوع مهمة غير معروف: {job.kind}")


def _claim(db: Session, stmt):
    if is_postgres():
        stmt = stmt.with_for_update(skip_locked=True)
    return db.scalars(stmt).all()


def process_jobs(limit: int = 4) -> int:
    done = 0
    db = SessionLocal()
    try:
        jobs = _claim(db, select(Job).where(Job.status == "queued").order_by(Job.created_at).limit(limit))
        for job in jobs:
            job.status, job.started_at = "running", datetime.now(timezone.utc)
        db.commit()
        for job in jobs:
            try:
                job.result = run_job(db, job)
                job.status = "done"
            except AIError as exc:
                db.rollback()
                job.status, job.error = "failed", f"{exc.code}: {exc.message}"
            except Exception as exc:  # keep the worker alive
                db.rollback()
                log.exception("job %s failed", job.id)
                job.status, job.error = "failed", f"internal: {exc}"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            done += 1
    finally:
        db.close()
    return done


def process_due_posts(limit: int = 10) -> int:
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    count = 0
    try:
        posts = _claim(db, select(Post).where(Post.status == "scheduled", Post.scheduled_at <= now)
                       .order_by(Post.scheduled_at).limit(limit))
        for post in posts:
            post.status = "publishing"
        db.commit()
        for post in posts:
            results = publish_post(db, post)
            post.attempts += 1
            post.publish_results = {**(post.publish_results or {}), **results}
            failed = [k for k, v in results.items() if not v.get("ok")]
            if not failed:
                post.status, post.error = "published", ""
            elif post.attempts < MAX_PUBLISH_ATTEMPTS and len(failed) < len(results):
                # partial failure: retry only the failed platforms
                post.platforms, post.status = failed, "scheduled"
                post.scheduled_at = now + timedelta(minutes=5)
                post.error = "; ".join(f"{k}: {results[k].get('error')}" for k in failed)
            else:
                post.status = "failed" if len(failed) == len(results) else "published"
                post.error = "; ".join(f"{k}: {results[k].get('error')}" for k in failed)
            db.commit()
            count += 1
    finally:
        db.close()
    return count


def tick() -> None:
    process_jobs()
    process_due_posts()
