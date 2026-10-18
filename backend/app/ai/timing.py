"""Posting-time guidance per market.

These are general starting points, not measurements from the owner's account. Replace them with each
account's own best hours once enough published posts have metrics.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from .catalog import DEFAULT_TZ, TIMEZONES

BEST_TIMES = {
    "SA": {"default": "21:00", "slots": ["13:00", "21:00", "22:30"], "note": "المساء بعد العشاء غالباً أعلى تفاعل في السعودية"},
    "EG": {"default": "20:00", "slots": ["14:00", "20:00", "22:30"], "note": "بعد الشغل وبالليل غالباً أعلى تفاعل في مصر"},
}
WEEKDAYS_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


def brand_tz(brief: dict) -> str:
    tz = (brief or {}).get("timezone")
    return tz if tz in TIMEZONES else DEFAULT_TZ.get((brief or {}).get("market"), "Africa/Cairo")


def best_times(brief: dict) -> dict:
    market = (brief or {}).get("market", "EG")
    return {"timezone": brand_tz(brief), **BEST_TIMES.get(market, BEST_TIMES["EG"]), "source": "guideline"}


def local_to_utc(local: str, tz: str) -> datetime:
    """'YYYY-MM-DDTHH:MM' wall-clock time in tz -> aware UTC datetime."""
    naive = datetime.fromisoformat(local)
    return naive.replace(tzinfo=ZoneInfo(tz)).astimezone(ZoneInfo("UTC"))


def now_local(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))
