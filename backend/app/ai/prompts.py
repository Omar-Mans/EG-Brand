"""Prompt templates. Version them: every change here changes product quality."""

import json

from .catalog import DIALECTS, FONTS_AR, FONTS_EN, ICONS, MARKETS, MONTHS_AR

PROMPT_VERSION = "2026-10-a"


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


def calendar(brief: dict, dna: dict, year: int, month: int, days_in_month: int, occasions: list[dict], count: int = 12) -> str:
    occ = " | ".join(f'{o["day"]}: {o["title"]}' for o in occasions) or "none"
    return f"""You are the content strategist inside EG Brand. Plan {count} social media posts for {MONTHS_AR[month - 1]} {year} (days 1-{days_in_month}) for this brand.
Business: {brief.get("idea", "")}
Brand DNA: {json.dumps(_brand_summary(dna), ensure_ascii=False)}
Market: {MARKETS.get(brief.get("market"), MARKETS["EG"])["label"]}. Write every Arabic text in this dialect: {DIALECTS.get(brief.get("dialect"), DIALECTS["msa"])}.
Occasions this month in this market (use the relevant ones on their dates; never invent public holidays): {occ}
Mix formats: about 7 "post", 3 "reel", 2 "story". Spread posts across the month. Follow the pillar shares. Be specific to this business, not generic.
Each item: {{"day":integer,"time":"HH:MM","format":"post|reel|story","pillar":"one of the pillar names","occasion":"occasion name from the list or empty string","headline":"Arabic, max 6 words, printed on the design","caption":"2-4 short lines in the dialect","hashtags":["3-5 hashtags"],"cta":"short Arabic call to action"}}
Reply with ONLY a JSON array of {count} such objects sorted by day."""


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
