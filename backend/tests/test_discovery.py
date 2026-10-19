"""Client discovery questionnaire, AI strategy, safe website reading, free photo providers and the cron endpoint."""

import base64

import httpx
import pytest

from app import jobs
from app.ai import images, prompts, services, website
from app.config import get_settings

from .conftest import register
from .test_flow import make_brand, run_job

ANSWERS = {"sector": "عربيات", "offer": "عربيات مستعملة مضمونة", "customer": "موظفين من 25 لـ 40 في الرياض",
           "pains": "خايفين من عربية فيها عيوب", "why_buy": "فحص كامل وضمان", "goal": "رسايل واستفسارات",
           "ads_budget": "أقل من 1,000", "platforms_now": ["انستجرام", "حاجة مش في القايمة"], "price_level": "غلط"}


def test_discovery_strategy_and_context(client, monkeypatch):
    h = register(client)
    brand = make_brand(client, h)
    bid = brand["id"]
    qs = client.get("/api/discovery/questions").json()
    assert "goal" in qs["required"] and qs["sections"][0]["questions"]

    assert client.post(f"/api/brands/{bid}/strategy", headers=h).status_code == 409  # nothing answered yet
    saved = client.put(f"/api/brands/{bid}/discovery", headers=h, json={"answers": ANSWERS}).json()["discovery"]["answers"]
    assert saved["platforms_now"] == ["انستجرام"] and "price_level" not in saved  # unknown options are dropped

    fu = run_job(client, h, client.post(f"/api/brands/{bid}/discovery/followups", headers=h).json())["result"]["followups"]
    assert len(fu) == 4
    d = client.put(f"/api/brands/{bid}/discovery/followups", headers=h, json={"answers": ["تقسيط مع بنك", "", "", ""]}).json()["discovery"]
    assert d["followups"][0]["answer"] == "تقسيط مع بنك"

    st = run_job(client, h, client.post(f"/api/brands/{bid}/strategy", headers=h).json())["result"]["strategy"]
    assert sum(p["share"] for p in st["content_pillars"]) in (99, 100, 101)
    assert len(st["roadmap"]) == 3 and st["currency"] == "SAR"

    # The identity follows the strategy, and every prompt now carries the client's answers.
    seen = []
    real = prompts.brand_dna
    monkeypatch.setattr(prompts, "brand_dna", lambda brief, context="": seen.append(context) or real(brief, context))
    run_job(client, h, client.post(f"/api/brands/{bid}/generate-dna", headers=h).json())
    assert "فحص كامل وضمان" in seen[0] and "تقسيط مع بنك" in seen[0] and "Positioning" in seen[0]
    b = client.get(f"/api/brands/{bid}", headers=h).json()
    assert [p["name"] for p in b["dna"]["pillars"]] == [p["name"] for p in st["content_pillars"]]

    # Calendar size follows the strategy's cadence: max 3 posts/week -> 13 a month.
    run_job(client, h, client.post(f"/api/brands/{bid}/calendar", headers=h, json={"year": 2026, "month": 12}).json())
    assert len(client.get(f"/api/brands/{bid}/posts?month=2026-12", headers=h).json()) == 13


def test_normalize_strategy_rejects_and_fixes():
    with pytest.raises(services.AIError):
        services.normalize_strategy({"summary": "x"})
    st = services.normalize_strategy({"summary": "s", "content_pillars": [{"name": "a", "share": 30}, {"name": "b", "share": 30}],
                                      "roadmap": [{"actions": ["x"]}], "channels": [{"platform": "TikTok", "priority": "urgent", "posts_per_week": 99}],
                                      "budget": {"monthly_total": "abc"}})
    assert [p["share"] for p in st["content_pillars"]] == [50, 50]
    assert st["roadmap"][0]["phase"] == "الشهر الأول" and st["budget"]["monthly_total"] == 0
    assert st["channels"][0] == {**st["channels"][0], "priority": "medium", "posts_per_week": 21}


@pytest.mark.parametrize("url", ["http://127.0.0.1:8000", "http://localhost/admin", "http://169.254.169.254/latest", "http://10.0.0.5", "ftp://x.com"])
def test_website_blocks_private_addresses(url):
    with pytest.raises(website.WebsiteError):
        website.fetch_text(url)


def test_website_failure_is_not_fatal(client, monkeypatch):
    h = register(client)
    bid = make_brand(client, h)["id"]
    client.put(f"/api/brands/{bid}/discovery", headers=h, json={"answers": {**ANSWERS, "website": "http://127.0.0.1/"}})
    run_job(client, h, client.post(f"/api/brands/{bid}/discovery/followups", headers=h).json())
    d = client.get(f"/api/brands/{bid}", headers=h).json()["discovery"]
    assert d["website_error"] and not d["website_text"] and len(d["followups"]) == 4


def test_html_to_text():
    t = website.html_to_text("<html><title>معرض النور</title><meta name='description' content='عربيات مضمونة'><script>x()</script><p>أهلاً &amp; سهلاً</p></html>")
    assert t.startswith("معرض النور | عربيات مضمونة") and "x()" not in t and "أهلاً & سهلاً" in t


class FakeClient:
    """Stands in for httpx.Client inside images.py."""

    def __init__(self, *a, **k):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, **kw):
        assert "api.cloudflare.com" in url and kw["json"]["steps"] == 4
        return httpx.Response(200, json={"result": {"image": base64.b64encode(b"\xff\xd8\xffjpeg").decode()}, "success": True})

    def get(self, url, **kw):
        if "pixabay.com/api" in url:
            assert kw["params"]["orientation"] == "all" and kw["params"]["key"] == "pb"
            return httpx.Response(200, json={"hits": [{"user": "Sara", "pageURL": "https://pixabay.com/p/2",
                                                       "largeImageURL": "https://pixabay.com/get/2.jpg"}]})
        if "api.pexels.com" in url:
            assert kw["params"]["orientation"] == "square"
            return httpx.Response(200, json={"photos": [{"photographer": "Ali", "url": "https://pexels.com/p/1",
                                                         "src": {"large2x": "https://images.pexels.com/1.jpg", "portrait": "x"}}]})
        return httpx.Response(200, content=b"\xff\xd8\xffphoto", headers={"content-type": "image/jpeg"})


def _first_post(client, h):
    bid = make_brand(client, h)["id"]
    run_job(client, h, client.post(f"/api/brands/{bid}/generate-dna", headers=h).json())
    run_job(client, h, client.post(f"/api/brands/{bid}/calendar", headers=h, json={"year": 2026, "month": 11}).json())
    return next(p for p in client.get(f"/api/brands/{bid}/posts?month=2026-11", headers=h).json() if p["format"] == "post")


def test_free_photo_providers(client, monkeypatch):
    h = register(client)
    post = _first_post(client, h)
    s = get_settings()
    monkeypatch.setattr(images.httpx, "Client", FakeClient)

    monkeypatch.setattr(s, "image_provider", "cloudflare")
    run_job(client, h, client.post(f"/api/posts/{post['id']}/background", headers=h, json={}).json())

    monkeypatch.setattr(s, "pixabay_api_key", "pb")
    run_job(client, h, client.post(f"/api/posts/{post['id']}/background", headers=h, json={"source": "stock"}).json())
    p = next(x for x in client.get(f"/api/brands/{post['brand_id']}/posts?month=2026-11", headers=h).json() if x["id"] == post["id"])
    assert p["design"]["photo_credit"] == {"name": "Sara", "url": "https://pixabay.com/p/2", "source": "Pixabay"}

    monkeypatch.setattr(s, "pexels_api_key", "k")  # Pexels wins when both keys exist
    run_job(client, h, client.post(f"/api/posts/{post['id']}/background", headers=h, json={"source": "stock", "prompt": "car showroom"}).json())
    p = next(x for x in client.get(f"/api/brands/{post['brand_id']}/posts?month=2026-11", headers=h).json() if x["id"] == post["id"])
    assert p["bg_url"].endswith(".jpg") and p["design"]["photo_credit"]["name"] == "Ali"
    assert p["design"]["layout"] in ("photo_overlay", "photo_split")


def test_stock_without_key_explains(client, monkeypatch):
    h = register(client)
    post = _first_post(client, h)
    monkeypatch.setattr(type(get_settings()), "stock_backend", property(lambda self: ""))
    job = client.post(f"/api/posts/{post['id']}/background", headers=h, json={"source": "stock"}).json()
    jobs.process_jobs()
    assert "PIXABAY_API_KEY" in client.get(f"/api/jobs/{job['id']}", headers=h).json()["error"]


def test_cron_tick_needs_secret(client, monkeypatch):
    assert client.post("/api/cron/tick").status_code == 403
    monkeypatch.setattr(get_settings(), "cron_secret", "s3cret")
    assert client.post("/api/cron/tick", headers={"X-Cron-Secret": "nope"}).status_code == 403
    assert client.post("/api/cron/tick", headers={"X-Cron-Secret": "s3cret"}).json() == {"jobs": 0, "posts": 0}
    assert "stock" in client.get("/api/health").json()
