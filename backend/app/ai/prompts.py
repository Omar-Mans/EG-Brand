"""Prompt templates. Version them: every change here changes product quality."""

import json

from .catalog import DIALECTS, FONTS_AR, FONTS_EN, ICONS, LAYOUTS, MARKETS, MONTHS_AR

PROMPT_VERSION = "2026-10-b"


def brand_dna(brief: dict) -> str:
    name = (brief.get("name") or "").strip()
    return f"""You are the brand strategist inside "EG Brand", an Arabic-first branding platform for small businesses.
Create a complete brand identity for this business. Every human-facing text value must be in Arabic, written in this dialect: {DIALECTS.get(brief.get("dialect"), DIALECTS["msa"])}, except fields ending in _en which are English.

Business idea: {brief.get("idea", "")}
Market: {MARKETS.get(brief.get("market"), MARKETS["EG"])["label"]}
Preferred brand name: {name or "none, propose names"}
Style keywords: {"، ".join(brief.get("styles") or []) or "no preference"}
Preferred colors (hex): {", ".join(brief.get("colors") or []) or "no preference"}

Reply with ONLY one JSON object with exactly these keys:
{{"names":[{{"ar":"Arabic name","en":"Latin transliteration or English name","meaning":"one short Arabic sentence why"}}],
"tagline_ar":"short Arabic tagline, max 5 words","tagline_en":"English tagline, max 6 words",
"positioning":"one Arabic sentence","audience":"one Arabic sentence describing the target customer",
"personality":["4 Arabic adjectives"],"tone":"one Arabic sentence on tone of voice",
"voice_do":["3 short Arabic rules"],"voice_dont":["3 short Arabic rules"],
"palette":[{{"role":"primary","name":"Arabic color name","hex":"#RRGGBB"}},{{"role":"secondary","name":"","hex":""}},{{"role":"accent","name":"","hex":""}},{{"role":"dark","name":"","hex":""}},{{"role":"light","name":"","hex":""}}],
"font_ar":"one of {json.dumps(FONTS_AR, ensure_ascii=False)}","font_en":"one of {json.dumps(FONTS_EN)}",
"icon":"one of {json.dumps(ICONS)}",
"pillars":[{{"name":"Arabic content pillar","share":40}}]}}
Rules: exactly 3 names{f', and names[0] must be exactly "{name}"' if name else ""}; Arabic names 1-2 words, easy to say. Exactly 4 pillars whose shares sum to 100. "dark" must be very dark and "light" very light so text is readable on both; primary must contrast with light. Pick the font and icon that best fit the personality."""


def _brand_summary(dna: dict) -> dict:
    names = dna.get("names") or [{}]
    chosen = names[min(dna.get("chosen", 0), len(names) - 1)]
    return {
        "name": chosen, "tagline": dna.get("tagline_ar"), "positioning": dna.get("positioning"),
        "audience": dna.get("audience"), "personality": dna.get("personality"), "tone": dna.get("tone"),
        "do": dna.get("voice_do"), "dont": dna.get("voice_dont"), "pillars": dna.get("pillars"),
    }


POST_FIELDS = f"""{{"time":"HH:MM","format":"post|reel|story","pillar":"one of the pillar names","occasion":"occasion name from the list or empty string",
"headline":"Arabic hook, max 6 words, printed big on the design","subheadline":"Arabic supporting line, max 10 words, printed under the headline, or empty",
"badge":"very short Arabic label for a corner badge such as 'خصم 20%' or 'جديد' or 'لفترة محدودة', or empty",
"layout":"one of {json.dumps(LAYOUTS)}","visual_prompt":"English description of the background photo for this post",
"caption":"2-4 short lines in the dialect","hashtags":["3-5 hashtags"],"cta":"short Arabic call to action"}}"""

DESIGN_RULES = """Work like a senior social media designer and art director:
- The headline is a hook, not a sentence. Put the price, number or benefit in it when there is one.
- layout: "offer" only for promotions and always with a badge; "quote" for customer reviews and testimonials;
  "photo_overlay" or "photo_split" for product, place and lifestyle posts; "bold" for announcements and tips; "minimal" for brand and premium moments. Mix layouts across the month.
- visual_prompt: a photorealistic commercial photo that matches the business and post (for a car dealer: the actual type of car, showroom, road; for food: the dish).
  Describe subject, setting, light and camera angle. Never ask for text, letters, logos or watermarks in the photo. Leave clean space for text."""


def calendar(brief: dict, dna: dict, year: int, month: int, days_in_month: int, occasions: list[dict], count: int = 12) -> str:
    occ = " | ".join(f'{o["day"]}: {o["title"]}' for o in occasions) or "none"
    return f"""You are the content strategist inside EG Brand. Plan {count} social media posts for {MONTHS_AR[month - 1]} {year} (days 1-{days_in_month}) for this brand.
Business: {brief.get("idea", "")}
Brand DNA: {json.dumps(_brand_summary(dna), ensure_ascii=False)}
Market: {MARKETS.get(brief.get("market"), MARKETS["EG"])["label"]}. Write every Arabic text in this dialect: {DIALECTS.get(brief.get("dialect"), DIALECTS["msa"])}.
Occasions this month in this market (use the relevant ones on their dates; never invent public holidays): {occ}
Mix formats: about 7 "post", 3 "reel", 2 "story". Spread posts across the month. Follow the pillar shares. Be specific to this business, not generic.
{DESIGN_RULES}
Each item: {{"day":integer, ...}} with these fields: {POST_FIELDS}
Reply with ONLY a JSON array of {count} such objects sorted by day."""


def posts_for_dates(brief: dict, dna: dict, dates: list[str], occasions: list[str], topic: str) -> str:
    return f"""You are the content strategist inside EG Brand. Write one social media post for each of these dates: {", ".join(dates)}.
Business: {brief.get("idea", "")}
Brand DNA: {json.dumps(_brand_summary(dna), ensure_ascii=False)}
Market: {MARKETS.get(brief.get("market"), MARKETS["EG"])["label"]}. Write every Arabic text in this dialect: {DIALECTS.get(brief.get("dialect"), DIALECTS["msa"])}.
Focus requested by the owner: {topic or "a balanced mix of the brand pillars"}
Occasions on these dates (use only if relevant; never invent holidays): {", ".join(occasions) or "none"}
Use mostly "post" format. Vary the angle every day.
{DESIGN_RULES}
Each item: {{"date":"YYYY-MM-DD", ...}} with these fields: {POST_FIELDS}
Reply with ONLY a JSON array with exactly {len(dates)} objects, one per date, in date order."""


def agent_plan(command: str, today: str, weekday: str, tz: str, connected: list[str], best_time: str) -> str:
    return f"""You are the scheduling agent inside EG Brand, an Arabic social media platform. Turn the owner's command into a plan.
Today is {today} ({weekday}) in timezone {tz}. Connected platforms: {", ".join(connected) or "none"}.
Recommended posting time for this market when the owner does not give one: {best_time}.
Owner's command (Arabic): {command}
Reply with ONLY a JSON object:
{{"intent":"create_and_schedule" or "status" or "unsupported",
"count":number of posts (1-30),"start_date":"YYYY-MM-DD (tomorrow if not given)","every_days":days between posts (1 = daily),
"time":"HH:MM 24h","platforms":["subset of the connected platforms; all connected ones if none named"],
"topic":"short Arabic focus of the content, or empty","reply":"one short Arabic sentence telling the owner what you will do"}}
Use "status" when the owner asks what is scheduled or published. Use "unsupported" for anything else and explain in reply."""


def rewrite_post(brief: dict, dna: dict, post: dict, instruction: str) -> str:
    s = _brand_summary(dna)
    return f"""Rewrite this social media post for the Arabic brand "{s["name"].get("ar", "")}". Dialect: {DIALECTS.get(brief.get("dialect"), DIALECTS["msa"])}. Brand tone: {s["tone"]}. Do: {"; ".join(s["do"] or [])}. Don't: {"; ".join(s["dont"] or [])}.
User instruction: {instruction or "make it more engaging while keeping the meaning"}.
Current post: {json.dumps(post, ensure_ascii=False)}
Reply with ONLY a JSON object: {{"headline":"Arabic, max 6 words, shown on the design","caption":"2-4 short lines","hashtags":["#..."],"cta":"short Arabic call to action"}}"""


def ads_plan(brief: dict, dna: dict, objective: str, budget: float, currency: str, days: int, platforms: list[str]) -> str:
    s = _brand_summary(dna)
    return f"""You are the paid-ads planner inside EG Brand. Plan one paid social campaign.
Business: {brief.get("idea", "")}
Brand: {s["name"].get("ar", "")}; positioning: {s["positioning"]}; audience: {s["audience"]}; tone: {s["tone"]}
Market: {MARKETS.get(brief.get("market"), MARKETS["EG"])["label"]}. Write Arabic text in this dialect: {DIALECTS.get(brief.get("dialect"), DIALECTS["msa"])}.
Objective: {objective}. Total budget: {budget} {currency} over {days} days. Platforms allowed: {", ".join(platforms)}.
Reply with ONLY a JSON object: {{"audience":{{"age":"e.g. 18-30","gender":"Arabic","locations":["Arabic city or area names"],"interests":["4-6 Arabic interests"]}},"split":[{{"platform":"one of the allowed platforms","pct":number,"why":"one short Arabic sentence"}}],"ads":[{{"platform":"","headline":"Arabic, max 6 words","primary_text":"Arabic, 1-2 sentences","cta":"short Arabic button text"}}],"kpis":["3-4 Arabic metrics to watch for this objective"],"tips":["3 short practical Arabic tips"]}}
Rules: split covers only allowed platforms and pct sums to 100; exactly 3 ads; do not predict reach, clicks or sales numbers."""
