"""Prompt templates. Version them: every change here changes product quality."""

import json

from .catalog import DIALECTS, FONTS_AR, FONTS_EN, ICONS, LAYOUTS, MARKETS, MONTHS_AR

PROMPT_VERSION = "2026-10-c"


def _ctx(context: str) -> str:
    return f"\nWhat we know about this business (owner's discovery answers and the agreed strategy):\n{context}\n" if context else ""


def brand_dna(brief: dict, context: str = "") -> str:
    name = (brief.get("name") or "").strip()
    return f"""You are the brand strategist inside "EG Brand", an Arabic-first branding platform for small businesses.
Create a complete brand identity for this business. Every human-facing text value must be in Arabic, written in this dialect: {DIALECTS.get(brief.get("dialect"), DIALECTS["msa"])}, except fields ending in _en which are English.

Business idea: {brief.get("idea", "")}
Market: {MARKETS.get(brief.get("market"), MARKETS["EG"])["label"]}
Preferred brand name: {name or "none, propose names"}
Style keywords: {"، ".join(brief.get("styles") or []) or "no preference"}
Preferred colors (hex): {", ".join(brief.get("colors") or []) or "no preference"}
{_ctx(context)}
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
"photo_query":"2-4 English keywords to search a real stock photo for this post",
"caption":"2-4 short lines in the dialect","hashtags":["3-5 hashtags"],"cta":"short Arabic call to action"}}"""

DESIGN_RULES = """Work like a senior social media designer and art director:
- The headline is a hook, not a sentence. Put the price, number or benefit in it when there is one.
- layout: "offer" only for promotions and always with a badge; "quote" for customer reviews and testimonials;
  "photo_overlay" or "photo_split" for product, place and lifestyle posts; "bold" for announcements and tips; "minimal" for brand and premium moments. Mix layouts across the month.
- visual_prompt: a photorealistic commercial photo that matches the business and post (for a car dealer: the actual type of car, showroom, road; for food: the dish).
  Describe subject, setting, light and camera angle. Never ask for text, letters, logos or watermarks in the photo. Leave clean space for text."""


def calendar(brief: dict, dna: dict, year: int, month: int, days_in_month: int, occasions: list[dict], count: int = 12, context: str = "") -> str:
    occ = " | ".join(f'{o["day"]}: {o["title"]}' for o in occasions) or "none"
    return f"""You are the content strategist inside EG Brand. Plan {count} social media posts for {MONTHS_AR[month - 1]} {year} (days 1-{days_in_month}) for this brand.
Business: {brief.get("idea", "")}
Brand DNA: {json.dumps(_brand_summary(dna), ensure_ascii=False)}
Market: {MARKETS.get(brief.get("market"), MARKETS["EG"])["label"]}. Write every Arabic text in this dialect: {DIALECTS.get(brief.get("dialect"), DIALECTS["msa"])}.
Occasions this month in this market (use the relevant ones on their dates; never invent public holidays): {occ}
{_ctx(context)}Mix formats: about 7 "post", 3 "reel", 2 "story". Spread posts across the month. Follow the pillar shares. Be specific to this business, not generic.
{DESIGN_RULES}
Each item: {{"day":integer, ...}} with these fields: {POST_FIELDS}
Reply with ONLY a JSON array of {count} such objects sorted by day."""


def posts_for_dates(brief: dict, dna: dict, dates: list[str], occasions: list[str], topic: str, context: str = "") -> str:
    return f"""You are the content strategist inside EG Brand. Write one social media post for each of these dates: {", ".join(dates)}.
Business: {brief.get("idea", "")}
Brand DNA: {json.dumps(_brand_summary(dna), ensure_ascii=False)}
Market: {MARKETS.get(brief.get("market"), MARKETS["EG"])["label"]}. Write every Arabic text in this dialect: {DIALECTS.get(brief.get("dialect"), DIALECTS["msa"])}.
Focus requested by the owner: {topic or "a balanced mix of the brand pillars"}
{_ctx(context)}Occasions on these dates (use only if relevant; never invent holidays): {", ".join(occasions) or "none"}
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


def ads_plan(brief: dict, dna: dict, objective: str, budget: float, currency: str, days: int, platforms: list[str], context: str = "") -> str:
    s = _brand_summary(dna)
    return f"""You are the paid-ads planner inside EG Brand. Plan one paid social campaign.
Business: {brief.get("idea", "")}
Brand: {s["name"].get("ar", "")}; positioning: {s["positioning"]}; audience: {s["audience"]}; tone: {s["tone"]}
Market: {MARKETS.get(brief.get("market"), MARKETS["EG"])["label"]}. Write Arabic text in this dialect: {DIALECTS.get(brief.get("dialect"), DIALECTS["msa"])}.
Objective: {objective}. Total budget: {budget} {currency} over {days} days. Platforms allowed: {", ".join(platforms)}.
{_ctx(context)}Reply with ONLY a JSON object: {{"audience":{{"age":"e.g. 18-30","gender":"Arabic","locations":["Arabic city or area names"],"interests":["4-6 Arabic interests"]}},"split":[{{"platform":"one of the allowed platforms","pct":number,"why":"one short Arabic sentence"}}],"ads":[{{"platform":"","headline":"Arabic, max 6 words","primary_text":"Arabic, 1-2 sentences","cta":"short Arabic button text"}}],"kpis":["3-4 Arabic metrics to watch for this objective"],"tips":["3 short practical Arabic tips"]}}
Rules: split covers only allowed platforms and pct sums to 100; exactly 3 ads; do not predict reach, clicks or sales numbers."""


def discovery_followups(brief: dict, discovery_text: str) -> str:
    return f"""You are a senior marketing strategist at an agency in {MARKETS.get(brief.get("market"), MARKETS["EG"])["label"]}.
You are interviewing a new client before writing their marketing strategy. Here is what they told you:
Business idea: {brief.get("idea", "")}
{discovery_text}
Ask exactly 4 short follow-up questions that you still need to build a strong, specific strategy for THIS sector and THIS business
(for example for a car dealer: stock size, financing partners, warranty; for a restaurant: delivery apps, best dishes, busy hours).
Do not repeat what they already answered. Write each question in simple Arabic, dialect: {DIALECTS.get(brief.get("dialect"), DIALECTS["msa"])}.
Reply with ONLY a JSON array: [{{"question":"Arabic question","why":"one short Arabic sentence on why it matters"}}]"""


def strategy(brief: dict, discovery_text: str, currency: str, today: str) -> str:
    return f"""You are the head of strategy at a top marketing agency in {MARKETS.get(brief.get("market"), MARKETS["EG"])["label"]}.
Write a practical 90-day social media marketing strategy for this client, starting {today}. Base every recommendation on what the client told you;
when you assume something, say so. Never invent market statistics, follower numbers or results. KPI targets must be derived from the client's own
goal and baseline (if they gave none, propose a modest target and label it as a starting target). Prefer free and low-cost actions when the budget is small.
Write all text in clear Arabic, dialect: {DIALECTS.get(brief.get("dialect"), DIALECTS["msa"])}. Money in {currency}.

Business idea: {brief.get("idea", "")}
Client discovery:
{discovery_text}

Reply with ONLY one JSON object with these keys:
{{"summary":"3-4 sentence executive summary",
"diagnosis":{{"strengths":["3-4"],"weaknesses":["3-4"],"opportunities":["3-4"],"threats":["2-3"]}},
"positioning":{{"statement":"one sentence: for [who] who [need], we are [what] that [benefit], unlike [alternative]","usp":["3 unique selling points"],"proof_points":["3 proofs to show in content"]}},
"personas":[{{"name":"short Arabic persona name","age":"range","description":"2 sentences","pains":["3"],"motivations":["3"],"objections":["2-3"],"where":["platforms they use"],"message":"the one message that converts them"}}],
"channels":[{{"platform":"one of: Instagram, TikTok, Facebook, Snapchat, X, LinkedIn, YouTube, WhatsApp, Google","role":"what this channel does in the funnel","priority":"high|medium|low","posts_per_week":number,"formats":["e.g. Reels, Carousel, Stories"],"why":"one sentence"}}],
"content_pillars":[{{"name":"short pillar name","share":percentage,"goal":"what it achieves","examples":["3 concrete post ideas for this business"]}}],
"offers":[{{"title":"","description":"","when":"timing or season"}}],
"budget":{{"monthly_total":number,"split":[{{"item":"e.g. Instagram ads, content production","pct":percentage,"note":""}}],"note":"how to spend if the budget is zero or small"}},
"roadmap":[{{"phase":"الشهر الأول","goal":"","actions":["4-6 concrete actions"],"kpis":[{{"name":"","target":""}}]}}],
"quick_wins":["5 things to do in the first 7 days"],
"kpis":[{{"name":"","target":"","why":""}}],
"risks":[{{"risk":"","mitigation":""}}],
"competitors":[{{"name":"competitor name from the client or 'منافس مباشر'","their_strength":"","our_angle":"how we beat them"}}]}}
Rules: 2 or 3 personas; 2 to 4 channels ranked by priority; exactly 4 content pillars whose shares sum to 100; exactly 3 roadmap phases
(الشهر الأول, الشهر التاني, الشهر التالت); budget.monthly_total must respect the client's stated ad budget."""


def reel_script(brief: dict, dna: dict, post: dict, dialect: str, context: str = "") -> str:
    s = _brand_summary(dna)
    return f"""You are a senior short-form video creator writing a 15-25 second Instagram/TikTok reel for the Arabic brand "{s["name"].get("ar", "")}".
Business: {brief.get("idea", "")}. Tone: {s["tone"]}. Don't: {"; ".join(s["dont"] or [])}.
{_ctx(context)}The reel is based on this planned post: {json.dumps(post, ensure_ascii=False)}
The voice-over is read by a text-to-speech voice in this dialect: {DIALECTS.get(dialect, DIALECTS["msa"])}. Write the spoken lines exactly as people
talk in that dialect, short and natural, with no emojis, hashtags, symbols or English words (write numbers as words if they are short).

Structure: scene 1 is the hook (a question or a bold specific claim, understood in 2 seconds); the middle scenes show one benefit or proof each;
the last scene is the offer or the reason to act now. On-screen text is short and big; the voice says more than the screen.
Reply with ONLY one JSON object:
{{"scenes":[{{"text":"Arabic on-screen text, max 6 words","sub":"optional Arabic line, max 8 words, or empty","voice":"spoken line in the dialect, 6-16 words",
"photo_query":"2-4 English keywords for a real stock photo of this scene","visual_prompt":"English photo description for an AI image, photorealistic, no text"}}],
"outro_voice":"short spoken call to action in the dialect, max 8 words"}}
Rules: 3 to 5 scenes. Never invent prices, discounts, numbers or guarantees that are not in the post or the business facts above."""
