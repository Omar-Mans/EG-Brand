"""The live gateway path, with the provider call faked: fallback to the next model, token and cost recording."""

from types import SimpleNamespace

import pytest

from app.ai import llm
from app.config import get_settings
from app.db import SessionLocal
from app.models import Company, UsageEvent

from .conftest import register


@pytest.fixture()
def live(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "ai_mode", "live")
    monkeypatch.setattr(s, "llm_quality_models", "provider-a/down,provider-b/up")
    monkeypatch.setattr(s, "llm_price_overrides", "provider-b/up=2:10")
    calls = []

    def fake_completion(model, messages, **kw):
        calls.append(model)
        if model == "provider-a/down":
            raise RuntimeError("503 overloaded")
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='<think>x</think>{"ok": true}'))],
                               usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=500))

    import litellm
    monkeypatch.setattr(litellm, "completion", fake_completion)
    return calls


def test_fallback_and_cost(client, live):
    register(client)
    db = SessionLocal()
    company = db.query(Company).one()
    data = llm.complete_json(db, "prompt", company_id=company.id, feature="dna", tier="quality")
    assert data == {"ok": True}
    assert live == ["provider-a/down", "provider-b/up"]
    events = db.query(UsageEvent).order_by(UsageEvent.created_at).all()
    assert [e.ok for e in events] == [False, True]
    assert events[1].input_tokens == 1000 and events[1].output_tokens == 500
    assert events[1].cost_usd == pytest.approx(1000 / 1e6 * 2 + 500 / 1e6 * 10)
    db.close()
