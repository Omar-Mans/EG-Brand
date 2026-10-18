"""LLM gateway: one entry point for every AI call.

- Routes by tier ("fast" or "quality") through a fallback chain of models (LiteLLM model names).
- Parses JSON tolerantly.
- Records tokens and cost for every call against the company (UsageEvent).
- Enforces a monthly AI budget per company.
- In mock mode (no API keys) returns deterministic sample data so the whole product runs locally.
"""

import json
import logging
import re
import time
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Company, UsageEvent

log = logging.getLogger(__name__)


class AIError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3)  # Arabic-heavy text: roughly 3 characters per token


def parse_json(text: str):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if starts:
        start = min(starts)
        end = max(text.rfind("}"), text.rfind("]"))
        if end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    raise AIError("invalid_json", "رد الـ AI مكانش JSON صالح")


def month_spend(db: Session, company_id: str) -> float:
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = db.scalar(
        select(func.coalesce(func.sum(UsageEvent.cost_usd), 0.0)).where(
            UsageEvent.company_id == company_id, UsageEvent.created_at >= start
        )
    )
    return float(total or 0.0)


def _cost(model: str, response, in_tok: int, out_tok: int) -> float:
    overrides = get_settings().price_overrides()
    if model in overrides:
        pi, po = overrides[model]
        return in_tok / 1e6 * pi + out_tok / 1e6 * po
    try:
        import litellm

        return float(litellm.completion_cost(completion_response=response) or 0.0)
    except Exception:  # unknown model price
        log.warning("no price for model %s; set LLM_PRICE_OVERRIDES", model)
        return 0.0


def _record(db: Session, *, company_id: str, brand_id: str | None, feature: str, model: str,
            in_tok: int, out_tok: int, cost: float, ms: int, ok: bool) -> None:
    db.add(UsageEvent(company_id=company_id, brand_id=brand_id, feature=feature, model=model,
                      input_tokens=in_tok, output_tokens=out_tok, cost_usd=cost, latency_ms=ms, ok=ok))
    db.commit()


def complete_json(db: Session, prompt: str, *, company_id: str, feature: str, tier: str = "quality",
                  brand_id: str | None = None, mock: Callable[[], object] | None = None, max_tokens: int = 6000):
    s = get_settings()
    company = db.get(Company, company_id)
    budget = company.monthly_ai_budget_usd if company else s.default_monthly_ai_budget_usd
    if budget and month_spend(db, company_id) >= budget:
        raise AIError("budget_exceeded", "الشركة وصلت لحد ميزانية الـ AI الشهرية")

    if not s.ai_live:
        started = time.monotonic()
        data = mock() if mock else {}
        text = json.dumps(data, ensure_ascii=False)
        _record(db, company_id=company_id, brand_id=brand_id, feature=feature, model="mock",
                in_tok=estimate_tokens(prompt), out_tok=estimate_tokens(text), cost=0.0,
                ms=int((time.monotonic() - started) * 1000), ok=True)
        return data

    import litellm

    last_error: AIError | None = None
    for model in s.model_list(tier):
        started = time.monotonic()
        try:
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                timeout=s.llm_timeout_seconds,
            )
        except Exception as exc:  # provider down, rate limited, bad key: try the next model
            log.warning("model %s failed: %s", model, exc)
            _record(db, company_id=company_id, brand_id=brand_id, feature=feature, model=model,
                    in_tok=0, out_tok=0, cost=0.0, ms=int((time.monotonic() - started) * 1000), ok=False)
            last_error = AIError("upstream_error", f"{model}: {exc}")
            continue
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        in_tok = getattr(usage, "prompt_tokens", None) or estimate_tokens(prompt)
        out_tok = getattr(usage, "completion_tokens", None) or estimate_tokens(text)
        ms = int((time.monotonic() - started) * 1000)
        cost = _cost(model, response, in_tok, out_tok)
        try:
            data = parse_json(text)
        except AIError as exc:
            _record(db, company_id=company_id, brand_id=brand_id, feature=feature, model=model,
                    in_tok=in_tok, out_tok=out_tok, cost=cost, ms=ms, ok=False)
            last_error = exc
            continue
        _record(db, company_id=company_id, brand_id=brand_id, feature=feature, model=model,
                in_tok=in_tok, out_tok=out_tok, cost=cost, ms=ms, ok=True)
        return data
    raise last_error or AIError("no_models", "مفيش موديلات متظبطة للـ AI")
