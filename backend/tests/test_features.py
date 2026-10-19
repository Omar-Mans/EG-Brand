"""Agent, AI backgrounds, approval-triggered scheduling, timezones, Meta token connect, metrics, column migration."""

from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text

from app import db as dbmod
from app import jobs
from app.social import meta

from .conftest import register
from .test_flow import PNG, make_brand, run_job


def ready_brand(client, h):
    brand = make_brand(client, h)
    run_job(client, h, client.post(f"/api/brands/{brand['id']}/generate-dna", headers=h).json())
    return brand


def test_agent_plans_posts_and_approval_schedules_them(client):
    h = register(client)
    brand = ready_brand(client, h)
    for platform in ("instagram", "facebook"):
        client.post("/api/social/mock/connect", headers=h, json={"platform": platform})

    job = client.post(f"/api/brands/{brand['id']}/agent", headers=h, json={"command": "جهزلي محتوى أسبوع وانشر كل يوم الساعة 9 بالليل"}).json()
    result = run_job(client, h, job)["result"]
    assert result["intent"] == "create_and_schedule" and len(result["post_ids"]) == 7
    posts = [p for m in result["months"] for p in client.get(f"/api/brands/{brand['id']}/posts?month={m}", headers=h).json()]
    planned = [p for p in posts if p["id"] in result["post_ids"]]
    assert all(p["design"]["plan"]["platforms"] == ["facebook", "instagram"] for p in planned)
    assert all(p["design"]["layout"] for p in planned)

    p = planned[0]
    client.post(f"/api/posts/{p['id']}/image", headers=h, files={"file": ("p.png", PNG, "image/png")})
    approved = client.patch(f"/api/posts/{p['id']}", headers=h, json={"approved": True}).json()
    assert approved["status"] == "scheduled" and approved["platforms"] == ["facebook", "instagram"]

    status = run_job(client, h, client.post(f"/api/brands/{brand['id']}/agent", headers=h, json={"command": "وريني الحالة"}).json())
    assert status["result"]["intent"] in ("create_and_schedule", "status")  # mock always plans; live model returns status


def test_backgrounds_and_design_edits(client):
    h = register(client)
    brand = ready_brand(client, h)
    run_job(client, h, client.post(f"/api/brands/{brand['id']}/calendar", headers=h, json={"year": 2026, "month": 11}).json())
    result = run_job(client, h, client.post(f"/api/brands/{brand['id']}/images", headers=h, json={"month": "2026-11"}).json())["result"]
    posts = client.get(f"/api/brands/{brand['id']}/posts?month=2026-11", headers=h).json()
    photo = [p for p in posts if p["design"]["layout"] in ("photo_overlay", "photo_split")]
    assert photo and len(result["post_ids"]) == len(photo) and all(p["bg_url"] for p in photo)
    assert all(not p["bg_url"] for p in posts if p not in photo)  # text layouts keep their look

    pid = posts[0]["id"]
    r = client.patch(f"/api/posts/{pid}", headers=h, json={"layout": "offer", "badge": "خصم 30%", "subheadline": "لحد آخر الشهر"})
    assert r.json()["design"]["layout"] == "offer" and r.json()["design"]["badge"] == "خصم 30%"
    assert client.patch(f"/api/posts/{pid}", headers=h, json={"layout": "nope"}).status_code == 422

    r = client.post(f"/api/posts/{pid}/background/upload", headers=h, files={"file": ("car.jpg", b"\xff\xd8\xff" + b"0" * 50, "image/jpeg")})
    assert r.json()["bg_url"].endswith(".jpg") and r.json()["design"]["layout"] == "photo_overlay"

    run_job(client, h, client.post(f"/api/posts/{pid}/background", headers=h, json={"prompt": "white SUV in a showroom"}).json())
    usage = client.get("/api/usage/summary", headers=h).json()
    assert any(f["feature"] == "image" for f in usage["by_feature"])


def test_schedule_in_brand_timezone(client):
    h = register(client)
    brand = ready_brand(client, h)  # Saudi brand -> Asia/Riyadh (UTC+3)
    assert client.get(f"/api/brands/{brand['id']}", headers=h).json()["brief"]["timezone"] == "Asia/Riyadh"
    assert client.get(f"/api/brands/{brand['id']}/best-times", headers=h).json()["default"] == "21:00"
    run_job(client, h, client.post(f"/api/brands/{brand['id']}/calendar", headers=h, json={"year": 2030, "month": 1}).json())
    pid = client.get(f"/api/brands/{brand['id']}/posts", headers=h).json()[0]["id"]
    client.post(f"/api/posts/{pid}/image", headers=h, files={"file": ("p.png", PNG, "image/png")})
    client.patch(f"/api/posts/{pid}", headers=h, json={"approved": True})
    client.post("/api/social/mock/connect", headers=h, json={"platform": "instagram"})
    r = client.post(f"/api/posts/{pid}/schedule", headers=h, json={"local_at": "2030-01-05T21:00", "platforms": ["instagram"]})
    assert datetime.fromisoformat(r.json()["scheduled_at"]) == datetime(2030, 1, 5, 18, 0, tzinfo=timezone.utc)


def test_meta_token_connect_and_metrics(client, monkeypatch):
    h = register(client)
    assets = {"pages": [{"id": "111", "name": "سيارتنا", "access_token": "PAGE_TOKEN",
                         "instagram_business_account": {"id": "222", "username": "sayaratna"}}], "ad_accounts": []}
    monkeypatch.setattr(meta, "assets_from_token", lambda t: (t, assets))
    r = client.post("/api/social/meta/token", headers=h, json={"token": "EAAB" + "x" * 40})
    assert {a["platform"] for a in r.json()} == {"facebook", "instagram"}

    published = []
    monkeypatch.setattr(meta, "publish_facebook", lambda *a: published.append("fb") or "111_999")
    monkeypatch.setattr(meta, "publish_instagram", lambda *a: published.append("ig") or "333")
    monkeypatch.setattr(meta, "post_metrics", lambda platform, i, t: {"likes": 5, "comments": 1} if platform == "facebook" else {"likes": 9})

    brand = ready_brand(client, h)
    run_job(client, h, client.post(f"/api/brands/{brand['id']}/calendar", headers=h, json={"year": 2030, "month": 2}).json())
    pid = client.get(f"/api/brands/{brand['id']}/posts", headers=h).json()[0]["id"]
    client.post(f"/api/posts/{pid}/image", headers=h, files={"file": ("p.png", PNG, "image/png")})
    client.patch(f"/api/posts/{pid}", headers=h, json={"approved": True})
    client.post(f"/api/posts/{pid}/schedule", headers=h, json={"scheduled_at": "2020-01-01T00:00:00Z", "platforms": ["facebook", "instagram"]})
    assert jobs.process_due_posts() == 1 and sorted(published) == ["fb", "ig"]
    m = client.post(f"/api/posts/{pid}/metrics", headers=h).json()
    assert m["metrics"] == {"facebook": {"likes": 5, "comments": 1}, "instagram": {"likes": 9}}


def test_metrics_never_invented_for_mock_accounts(client):
    h = register(client)
    brand = ready_brand(client, h)
    client.post("/api/social/mock/connect", headers=h, json={"platform": "instagram"})
    run_job(client, h, client.post(f"/api/brands/{brand['id']}/calendar", headers=h, json={"year": 2030, "month": 3}).json())
    pid = client.get(f"/api/brands/{brand['id']}/posts", headers=h).json()[0]["id"]
    client.post(f"/api/posts/{pid}/image", headers=h, files={"file": ("p.png", PNG, "image/png")})
    client.patch(f"/api/posts/{pid}", headers=h, json={"approved": True})
    client.post(f"/api/posts/{pid}/schedule", headers=h, json={"scheduled_at": "2020-01-01T00:00:00Z", "platforms": ["instagram"]})
    jobs.process_due_posts()
    m = client.post(f"/api/posts/{pid}/metrics", headers=h).json()
    assert m["metrics"] == {} and m["notes"]


def test_columns_added_to_existing_table(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path}/old.db")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE posts (id VARCHAR(32) PRIMARY KEY, headline TEXT)"))
    monkeypatch.setattr(dbmod, "engine", engine)
    dbmod.ensure_columns()
    cols = {c["name"] for c in inspect(engine).get_columns("posts")}
    assert {"design", "bg_url", "metrics", "metrics_at"} <= cols


def test_meta_network_failure_is_reported_not_crashing(client, monkeypatch):
    import httpx

    class DownClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, *a, **k): raise httpx.ConnectError("no route")
        post = get

    monkeypatch.setattr(meta.httpx, "Client", DownClient)
    h = register(client)
    r = client.post("/api/social/meta/token", headers=h, json={"token": "EAAB" + "x" * 40})
    assert r.status_code == 400 and "Meta" in r.json()["detail"]
