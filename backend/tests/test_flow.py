"""End-to-end flow with mock AI and mock social accounts:
register → brand → DNA → calendar → edit/approve/upload → schedule → worker publishes → ads → cost."""

from datetime import datetime, timedelta, timezone

from app import jobs
from app.ai.llm import parse_json

from .conftest import register

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def run_job(client, h, job):
    jobs.process_jobs()
    r = client.get(f"/api/jobs/{job['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "done", r.json().get("error")
    return r.json()


def make_brand(client, h):
    r = client.post("/api/brands", headers=h, json={"idea": "محل قهوة مختصة للشباب في الرياض", "name": "نورا",
                                                    "market": "SA", "dialect": "saudi", "styles": ["شبابي"], "colors": ["#D4A23C"]})
    assert r.status_code == 200, r.text
    return r.json()


def test_full_flow(client):
    h = register(client)
    brand = make_brand(client, h)

    job = client.post(f"/api/brands/{brand['id']}/generate-dna", headers=h).json()
    assert job["status"] == "queued"
    run_job(client, h, job)
    b = client.get(f"/api/brands/{brand['id']}", headers=h).json()
    assert b["dna"]["names"][0]["ar"] == "نورا"
    assert len(b["dna"]["palette"]) >= 5

    r = client.patch(f"/api/brands/{brand['id']}/dna", headers=h, json={"icon": "star8", "chosen": 1})
    assert r.json()["dna"]["icon"] == "star8" and r.json()["name"] == "حَبّة"

    job = client.post(f"/api/brands/{brand['id']}/calendar", headers=h, json={"year": 2026, "month": 11}).json()
    run_job(client, h, job)
    posts = client.get(f"/api/brands/{brand['id']}/posts", headers=h, params={"month": "2026-11"}).json()
    assert len(posts) == 12
    assert any(p["occasion"] == "الجمعة البيضاء" and p["day"] == 27 for p in posts)

    post = posts[0]
    r = client.patch(f"/api/posts/{post['id']}", headers=h, json={"headline": "صباحك نور", "approved": True})
    assert r.json()["approved"] is True

    # cannot schedule without an image or connected accounts
    at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    assert client.post(f"/api/posts/{post['id']}/schedule", headers=h, json={"scheduled_at": at, "platforms": ["instagram"]}).status_code == 409
    r = client.post(f"/api/posts/{post['id']}/image", headers=h, files={"file": ("p.png", PNG, "image/png")})
    assert r.status_code == 200 and r.json()["image_url"].endswith(".png")
    assert client.post(f"/api/posts/{post['id']}/schedule", headers=h, json={"scheduled_at": at, "platforms": ["instagram"]}).status_code == 409

    for platform in ("instagram", "facebook"):
        assert client.post("/api/social/mock/connect", headers=h, json={"platform": platform}).status_code == 200
    r = client.post(f"/api/posts/{post['id']}/schedule", headers=h, json={"scheduled_at": at, "platforms": ["instagram", "facebook"]})
    assert r.json()["status"] == "scheduled"

    assert jobs.process_due_posts() == 1
    published = client.get(f"/api/brands/{brand['id']}/posts", headers=h, params={"month": "2026-11"}).json()[0]
    assert published["status"] == "published"
    assert set(published["publish_results"]) == {"instagram", "facebook"}
    assert client.patch(f"/api/posts/{post['id']}", headers=h, json={"caption": "x"}).status_code == 409

    # rewrite another post with AI
    job = client.post(f"/api/posts/{posts[1]['id']}/regenerate", headers=h, json={"instruction": "أقصر"}).json()
    run_job(client, h, job)

    # ads plan → save → launch (no Meta ad account: marked ready, nothing spends)
    job = client.post(f"/api/brands/{brand['id']}/ads/plan", headers=h,
                      json={"objective": "وعي بالبراند", "budget": 1500, "days": 14, "platforms": ["Instagram + Facebook", "Snapchat"]}).json()
    plan = run_job(client, h, job)["result"]["plan"]
    assert round(sum(x["pct"] for x in plan["split"])) == 100 and plan["currency"] == "SAR"
    camp = client.post("/api/ads/campaigns", headers=h, json={"brand_id": brand["id"], "plan": plan}).json()
    assert client.post(f"/api/ads/campaigns/{camp['id']}/launch", headers=h).json()["status"] == "ready"

    # cost: every AI call is recorded against the company
    s = client.get("/api/usage/summary", headers=h).json()
    assert {f["feature"] for f in s["by_feature"]} == {"dna", "calendar", "regen", "ads"}
    econ = client.post("/api/usage/economics", headers=h, json={}).json()
    assert {m["market"] for m in econ["markets"]} == {"EG", "SA"}
    assert econ["monthly_cost_usd"] > 0


def test_tenants_are_isolated(client):
    h1 = register(client, "a@one.test", "شركة 1")
    h2 = register(client, "b@two.test", "شركة 2")
    brand = make_brand(client, h1)
    assert client.get(f"/api/brands/{brand['id']}", headers=h2).status_code == 404
    assert client.get("/api/brands", headers=h2).json() == []
    assert client.get("/api/usage/admin/companies", headers=h1).status_code == 403


def test_auth_errors(client):
    assert client.get("/api/brands").status_code == 401
    register(client)
    r = client.post("/api/auth/login", json={"email": "owner@cafe.test", "password": "wrong-password"})
    assert r.status_code == 401
    assert client.post("/api/auth/login", json={"email": "OWNER@cafe.test", "password": "secret-pass-1"}).status_code == 200


def test_budget_blocks_ai(client):
    from app.db import SessionLocal
    from app.models import Company, UsageEvent

    h = register(client)
    brand = make_brand(client, h)
    db = SessionLocal()
    company = db.query(Company).one()
    db.add(UsageEvent(company_id=company.id, feature="dna", model="x", cost_usd=company.monthly_ai_budget_usd))
    db.commit()
    db.close()
    job = client.post(f"/api/brands/{brand['id']}/generate-dna", headers=h).json()
    jobs.process_jobs()
    assert client.get(f"/api/jobs/{job['id']}", headers=h).json()["error"].startswith("budget_exceeded")


def test_parse_json_tolerant():
    assert parse_json('<think>hmm</think>```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Here you go: [1, 2] thanks') == [1, 2]
