"""Marketing calendar for Egypt and Saudi Arabia.

Hijri-based dates are approximate (they depend on moon sighting); extend OCC_DATED every year.
"""

import calendar

# (month, day, title, market) — market: SA | EG | both
OCC_FIXED = [
    (1, 1, "رأس السنة الميلادية", "both"),
    (2, 22, "يوم التأسيس", "SA"),
    (3, 21, "عيد الأم", "EG"),
    (8, 16, "العودة للمدارس", "SA"),
    (9, 23, "اليوم الوطني السعودي", "SA"),
    (9, 28, "العودة للمدارس", "EG"),
    (10, 1, "اليوم العالمي للقهوة", "both"),
    (10, 6, "ذكرى انتصارات أكتوبر", "EG"),
    (11, 11, "عروض 11.11", "both"),
    (12, 18, "اليوم العالمي للغة العربية", "both"),
    (12, 31, "ليلة رأس السنة", "both"),
]

# (year, month, day, title, market)
OCC_DATED = [
    (2027, 2, 8, "بداية رمضان (تقريبي)", "both"),
    (2027, 3, 10, "عيد الفطر (تقريبي)", "both"),
    (2027, 5, 16, "عيد الأضحى (تقريبي)", "both"),
]


def last_friday(year: int, month: int) -> int:
    day = calendar.monthrange(year, month)[1]
    while calendar.weekday(year, month, day) != 4:
        day -= 1
    return day


def occasions_for(year: int, month: int, market: str) -> list[dict]:
    items = [{"day": d, "title": t} for (m, d, t, mk) in OCC_FIXED if m == month and mk in ("both", market)]
    items += [{"day": d, "title": t} for (y, m, d, t, mk) in OCC_DATED if y == year and m == month and mk in ("both", market)]
    if month == 11:
        items.append({"day": last_friday(year, 11), "title": "الجمعة البيضاء"})
    return sorted(items, key=lambda o: o["day"])
