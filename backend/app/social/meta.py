"""Meta (Facebook Pages + Instagram Business) via the Graph API.

Needs a Meta app with Facebook Login and these permissions approved in App Review:
pages_show_list, pages_read_engagement, pages_manage_posts, instagram_basic, instagram_content_publish,
business_management (+ ads_management, ads_read for campaigns).
"""

import functools
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


def _network_safe(fn):
    """Turns connection failures and timeouts into MetaError so callers handle one error type."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except httpx.HTTPError as exc:
            raise MetaError(f"مش قادرين نوصل لـ Meta: {exc.__class__.__name__}") from exc
    return wrapper


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


@_network_safe
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


@_network_safe
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


@_network_safe
def assets_from_token(token: str) -> tuple[str, dict]:
    """Accepts a user token (Graph API Explorer or Facebook Login) or a Page token.

    Returns (token to store for ads, assets). User tokens are exchanged for a long-lived token when the
    Meta app id/secret are configured.
    """
    s = get_settings()
    if s.meta_app_id and s.meta_app_secret:
        try:
            with httpx.Client(timeout=30) as c:
                token = _check(c.get(f"{_graph()}/oauth/access_token", params={
                    "grant_type": "fb_exchange_token", "client_id": s.meta_app_id,
                    "client_secret": s.meta_app_secret, "fb_exchange_token": token}))["access_token"]
        except MetaError:
            pass  # page tokens and already long-lived tokens cannot always be exchanged; keep the original
    try:
        assets = list_assets(token)
        if assets["pages"]:
            return token, assets
    except MetaError:
        pass
    # A Page token: /me is the page itself
    with httpx.Client(timeout=30) as c:
        me = _check(c.get(f"{_graph()}/me", params={
            "access_token": token, "fields": "id,name,instagram_business_account{id,username}"}))
    if not me.get("id"):
        raise MetaError("التوكن ده مش مربوط بصفحة. استخدم توكن فيه صلاحية pages_show_list")
    page = {"id": me["id"], "name": me.get("name", ""), "access_token": token}
    if me.get("instagram_business_account"):
        page["instagram_business_account"] = me["instagram_business_account"]
    return token, {"pages": [page], "ad_accounts": []}


@_network_safe
def post_metrics(platform: str, external_id: str, token: str) -> dict:
    """Real engagement for one published post. Missing permissions just leave fields out."""
    out: dict = {}
    with httpx.Client(timeout=30) as c:
        if platform == "facebook":
            data = _check(c.get(f"{_graph()}/{external_id}", params={
                "access_token": token, "fields": "likes.summary(true).limit(0),comments.summary(true).limit(0),shares"}))
            out["likes"] = data.get("likes", {}).get("summary", {}).get("total_count")
            out["comments"] = data.get("comments", {}).get("summary", {}).get("total_count")
            out["shares"] = data.get("shares", {}).get("count", 0)
        elif platform == "instagram":
            data = _check(c.get(f"{_graph()}/{external_id}", params={"access_token": token, "fields": "like_count,comments_count"}))
            out["likes"], out["comments"] = data.get("like_count"), data.get("comments_count")
            try:
                ins = _check(c.get(f"{_graph()}/{external_id}/insights", params={"access_token": token, "metric": "reach"}))
                for row in ins.get("data", []):
                    if row.get("name") == "reach":
                        out["reach"] = (row.get("values") or [{}])[0].get("value")
            except MetaError:
                pass
    return {k: v for k, v in out.items() if v is not None}


@_network_safe
def publish_facebook(page_id: str, page_token: str, image_url: str, caption: str) -> str:
    with httpx.Client(timeout=60) as c:
        data = _check(c.post(f"{_graph()}/{page_id}/photos", data={
            "url": image_url, "caption": caption, "access_token": page_token}))
    return data.get("post_id") or data.get("id", "")


@_network_safe
def publish_facebook_video(page_id: str, page_token: str, video_url: str, caption: str) -> str:
    """Facebook downloads the MP4 from the public URL and posts it on the page."""
    with httpx.Client(timeout=180) as c:
        data = _check(c.post(f"{_graph()}/{page_id}/videos", data={
            "file_url": video_url, "description": caption, "access_token": page_token}))
    return data.get("id", "")


@_network_safe
def publish_instagram(ig_user_id: str, token: str, image_url: str, caption: str, fmt: str = "post", video_url: str | None = None) -> str:
    params = {"access_token": token}
    if video_url:  # reels (or a video story) need a public MP4 that Instagram downloads and processes
        params.update(video_url=video_url, media_type="STORIES" if fmt == "story" else "REELS")
        if fmt != "story":
            params.update(caption=caption, share_to_feed="true")
    else:
        params["image_url"] = image_url
        if fmt == "story":
            params["media_type"] = "STORIES"
        else:
            params["caption"] = caption  # without a video, a reel goes out as a feed image
    tries, wait = (60, 4) if video_url else (10, 2)
    with httpx.Client(timeout=120) as c:
        creation_id = _check(c.post(f"{_graph()}/{ig_user_id}/media", data=params))["id"]
        for _ in range(tries):  # wait until the container is ready (videos take a while)
            status = _check(c.get(f"{_graph()}/{creation_id}", params={"fields": "status_code", "access_token": token}))
            if status.get("status_code") in (None, "FINISHED"):
                break
            if status.get("status_code") == "ERROR":
                raise MetaError("Instagram رفض " + ("الفيديو" if video_url else "الصورة"))
            time.sleep(wait)
        else:
            raise MetaError("Instagram لسه بيجهز الفيديو، هنحاول تاني")
        data = _check(c.post(f"{_graph()}/{ig_user_id}/media_publish", data={"creation_id": creation_id, "access_token": token}))
    return data.get("id", "")


# ---- Ads (Marketing API). Campaigns are always created PAUSED: nothing spends until the owner turns it on in Ads Manager.

OBJECTIVE_MAP = {
    "وعي بالبراند": "OUTCOME_AWARENESS",
    "زيارات للمتجر أو الموقع": "OUTCOME_TRAFFIC",
    "رسائل واتساب": "OUTCOME_ENGAGEMENT",
    "مبيعات": "OUTCOME_SALES",
}


@_network_safe
def create_paused_campaign(ad_account_id: str, token: str, name: str, objective: str) -> str:
    act = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
    with httpx.Client(timeout=30) as c:
        data = _check(c.post(f"{_graph()}/{act}/campaigns", data={
            "name": name, "objective": OBJECTIVE_MAP.get(objective, "OUTCOME_AWARENESS"),
            "status": "PAUSED", "special_ad_categories": "[]", "access_token": token}))
    return data["id"]


@_network_safe
def campaign_insights(campaign_id: str, token: str) -> dict:
    with httpx.Client(timeout=30) as c:
        data = _check(c.get(f"{_graph()}/{campaign_id}/insights", params={
            "fields": "impressions,reach,clicks,spend,cpc,ctr", "access_token": token}))
    rows = data.get("data", [])
    return rows[0] if rows else {}
