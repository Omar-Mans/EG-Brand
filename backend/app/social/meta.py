"""Meta (Facebook Pages + Instagram Business) via the Graph API.

Needs a Meta app with Facebook Login and these permissions approved in App Review:
pages_show_list, pages_read_engagement, pages_manage_posts, instagram_basic, instagram_content_publish,
business_management (+ ads_management, ads_read for campaigns).
"""

import time
from urllib.parse import urlencode

import httpx

from ..config import get_settings

SCOPES = [
    "pages_show_list", "pages_read_engagement", "pages_manage_posts",
    "instagram_basic", "instagram_content_publish", "business_management",
    "ads_management", "ads_read",
]


class MetaError(Exception):
    pass


def _graph() -> str:
    return f"https://graph.facebook.com/{get_settings().meta_graph_version}"


def _check(resp: httpx.Response) -> dict:
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400 or "error" in data:
        err = data.get("error", {}) if isinstance(data, dict) else {}
        raise MetaError(err.get("message") or f"Meta API error {resp.status_code}")
    return data


def redirect_uri() -> str:
    s = get_settings()
    return f"{s.public_base_url.rstrip('/')}{s.meta_redirect_path}"


def login_url(state: str) -> str:
    s = get_settings()
    q = urlencode({"client_id": s.meta_app_id, "redirect_uri": redirect_uri(), "state": state,
                   "scope": ",".join(SCOPES), "response_type": "code"})
    return f"https://www.facebook.com/{s.meta_graph_version}/dialog/oauth?{q}"


def exchange_code(code: str) -> str:
    """Returns a long-lived user access token."""
    s = get_settings()
    with httpx.Client(timeout=30) as c:
        short = _check(c.get(f"{_graph()}/oauth/access_token", params={
            "client_id": s.meta_app_id, "client_secret": s.meta_app_secret,
            "redirect_uri": redirect_uri(), "code": code}))["access_token"]
        long = _check(c.get(f"{_graph()}/oauth/access_token", params={
            "grant_type": "fb_exchange_token", "client_id": s.meta_app_id,
            "client_secret": s.meta_app_secret, "fb_exchange_token": short}))
    return long["access_token"]


def list_assets(user_token: str) -> dict:
    """Pages (with page tokens and linked Instagram accounts) and ad accounts the user granted."""
    with httpx.Client(timeout=30) as c:
        pages = _check(c.get(f"{_graph()}/me/accounts", params={
            "access_token": user_token,
            "fields": "id,name,access_token,instagram_business_account{id,username}"})).get("data", [])
        try:
            ad_accounts = _check(c.get(f"{_graph()}/me/adaccounts", params={
                "access_token": user_token, "fields": "id,name,currency"})).get("data", [])
        except MetaError:
            ad_accounts = []
    return {"pages": pages, "ad_accounts": ad_accounts}


def publish_facebook(page_id: str, page_token: str, image_url: str, caption: str) -> str:
    with httpx.Client(timeout=60) as c:
        data = _check(c.post(f"{_graph()}/{page_id}/photos", data={
            "url": image_url, "caption": caption, "access_token": page_token}))
    return data.get("post_id") or data.get("id", "")


def publish_instagram(ig_user_id: str, token: str, image_url: str, caption: str, fmt: str = "post") -> str:
    params = {"image_url": image_url, "access_token": token}
    if fmt == "story":
        params["media_type"] = "STORIES"
    else:
        params["caption"] = caption  # reels need video; images go out as feed posts
    with httpx.Client(timeout=60) as c:
        creation_id = _check(c.post(f"{_graph()}/{ig_user_id}/media", data=params))["id"]
        for _ in range(10):  # wait until the container is ready
            status = _check(c.get(f"{_graph()}/{creation_id}", params={"fields": "status_code", "access_token": token}))
            if status.get("status_code") in (None, "FINISHED"):
                break
            if status.get("status_code") == "ERROR":
                raise MetaError("Instagram رفض الصورة")
            time.sleep(2)
        data = _check(c.post(f"{_graph()}/{ig_user_id}/media_publish", data={"creation_id": creation_id, "access_token": token}))
    return data.get("id", "")


# ---- Ads (Marketing API). Campaigns are always created PAUSED: nothing spends until the owner turns it on in Ads Manager.

OBJECTIVE_MAP = {
    "وعي بالبراند": "OUTCOME_AWARENESS",
    "زيارات للمتجر أو الموقع": "OUTCOME_TRAFFIC",
    "رسائل واتساب": "OUTCOME_ENGAGEMENT",
    "مبيعات": "OUTCOME_SALES",
}


def create_paused_campaign(ad_account_id: str, token: str, name: str, objective: str) -> str:
    act = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
    with httpx.Client(timeout=30) as c:
        data = _check(c.post(f"{_graph()}/{act}/campaigns", data={
            "name": name, "objective": OBJECTIVE_MAP.get(objective, "OUTCOME_AWARENESS"),
            "status": "PAUSED", "special_ad_categories": "[]", "access_token": token}))
    return data["id"]


def campaign_insights(campaign_id: str, token: str) -> dict:
    with httpx.Client(timeout=30) as c:
        data = _check(c.get(f"{_graph()}/{campaign_id}/insights", params={
            "fields": "impressions,reach,clicks,spend,cpc,ctr", "access_token": token}))
    rows = data.get("data", [])
    return rows[0] if rows else {}
