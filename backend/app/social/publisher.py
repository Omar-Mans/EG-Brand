"""Publishes one post to the platforms it is scheduled for, through the right provider."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Post, SocialAccount
from ..security import decrypt
from . import meta

SUPPORTED_LIVE = {"facebook", "instagram"}


def publish_post(db: Session, post: Post) -> dict:
    """Returns {platform: {"ok": bool, "id"|"error": str}} for every platform on the post."""
    results: dict = {}
    caption = post.caption + ("\n\n" + " ".join(post.hashtags) if post.hashtags else "")
    for platform in post.platforms or []:
        account = db.scalar(select(SocialAccount).where(
            SocialAccount.company_id == post.company_id, SocialAccount.platform == platform))
        if not account:
            results[platform] = {"ok": False, "error": "الحساب مش مربوط"}
            continue
        try:
            if account.provider == "mock":
                results[platform] = {"ok": True, "id": f"mock_{uuid.uuid4().hex[:10]}"}
            elif platform not in SUPPORTED_LIVE:
                results[platform] = {"ok": False, "error": "المنصة دي لسه مش مدعومة في النشر"}
            elif not post.image_url:
                results[platform] = {"ok": False, "error": "مفيش صورة للبوست"}
            elif platform == "facebook":
                results[platform] = {"ok": True, "id": meta.publish_facebook(
                    account.external_id, decrypt(account.access_token_enc), post.image_url, caption)}
            else:
                results[platform] = {"ok": True, "id": meta.publish_instagram(
                    account.external_id, decrypt(account.access_token_enc), post.image_url, caption, post.format)}
        except meta.MetaError as exc:
            results[platform] = {"ok": False, "error": str(exc)}
    return results
