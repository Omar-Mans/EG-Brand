# EG Brand v2: Product Brief (prompt for the build agent)

## Role
You are the founding product engineer and product designer of **EG Brand**, an Arabic-first AI marketing platform for small and
medium businesses in Egypt and Saudi Arabia. Turn the current MVP into a **market-ready product** that can be sold to several
business types this quarter. Work like a senior team (research, design, backend, AI, QA), not like a prototype builder.

## What already exists (read the repo before changing anything)
- FastAPI + SQLAlchemy backend, Postgres job queue and worker, Next.js 15 RTL frontend, LiteLLM gateway (Groq free tier) with
  per-company cost tracking and budget caps, mock modes for every external service.
- Client discovery questionnaire, then a 90-day AI strategy, then brand identity, monthly content plan, canvas-rendered post
  designs with real Arabic fonts, stock and AI photos, scheduling and publishing to Facebook and Instagram, real metrics,
  and an AI ads plan that creates **paused** Meta campaigns.
- Reels v1: AI script, then photo scenes, Saudi or Egyptian TTS voice-over, in-house synthesized music, then an ffmpeg render,
  published as Instagram Reels or a Facebook video.

## Non-negotiables
1. **Free first.** Every feature must run on free tiers or open-source tools. Name the paid upgrade path separately.
2. **Arabic first.** RTL everywhere. Egyptian and Saudi dialects are written as spoken, never "corrected" to MSA.
3. **Truth.** Never invent metrics, benchmarks, reviews or results. Targets come from the client's own numbers. Label every assumption.
4. **Human in control.** Nothing is published and no money is spent without explicit approval. Any "auto mode" runs only inside
   limits the owner sets, and every action is logged and can be undone.
5. **Security.** Secrets live only in `.env`. Tokens are encrypted at rest. Uploads are validated. Fetching outside URLs is
   protected against SSRF. Each company sees only its own data.
6. **Originality.** Learn from competitors, but never copy their name, copy text, visuals or templates.
7. **Done means tested.** Unit tests, an end-to-end browser test of each flow, a mobile check at 390px, and the existing suite green.

## Workstream 0: Market research and positioning (do this first, keep it short)
- Verify and compare these competitors from their own sites. Cite sources and mark anything unverified.
  - **Arabic content and reels:** Mohtwa (AI reel editing for Egyptian creators: raw upload, then silence and retake cutting,
    Egyptian captions, 8 templates, publishing; 399, 999 and 2,199 EGP per month), Nashrflow, Sahal AI, Adly AI, Scale by AI (Egypt).
  - **Global content tools:** Predis.ai, Ocoya, FeedHive, Canva.
  - **Video editing:** Submagic, Captions, OpusClip, CapCut.
  - **Media buying:** Madgicx, Birch (formerly Revealbot), AdCreative.ai, Smartly.
- Deliver `docs/research.md` with:
  - a feature-by-feature matrix
  - pricing per unit (per reel, per account, per month)
  - 3 to 5 target customer profiles (e.g. car dealers, restaurants, clinics, real estate, e-commerce, personal brands and creators)
  - the gaps we win on
  - one positioning sentence
  - a recommended pricing table in EGP and SAR with a margin check against our measured AI cost per company
- Working positioning, to refine with the data: *"Your AI marketing team in Arabic: it studies your business, plans,
  creates posts and reels, publishes, and runs your ads, with you approving every step."*
  Mohtwa does reel editing only. We cover the whole loop.

## Workstream 1: Brand, design system and product polish
- Propose a refined visual identity for EG Brand: logo mark, color tokens for light and dark themes, an Arabic and Latin type
  pairing, iconography and motion rules. Build it as CSS design tokens and a small component library (buttons, inputs, cards,
  tabs, steppers, empty states, toasts, modals, data tables, charts) and apply it to every screen.
- Add a public landing page (Arabic first, English second) with:
  - a hero
  - a 3-step "how it works"
  - a demo reel
  - vertical-specific sections
  - a pricing table
  - an FAQ
  - the "why not ChatGPT or CapCut" comparison
- Add onboarding that asks for the business type and loads a **vertical pack**. Each pack carries:
  - discovery questions
  - content pillars
  - KPIs
  - seasons and occasions
  - post and reel templates
  - ad audiences
- Fix any UX debt: consistent spacing, loading skeletons instead of text, clear errors, keyboard and screen-reader access.

## Workstream 2: Reels Studio v2 (AI editing of real footage)
Three modes on one screen.

### A. Script first (before filming)
- The user writes a script or asks the AI for one: hook, body and CTA, in their dialect, timed to 15, 30 or 60 seconds,
  using the strategy and vertical pack.
- Show it in a **teleprompter** view on the phone with adjustable speed, so the user records in one take.

### B. Raw upload (main mode)
The user uploads the phone video as shot. The pipeline then:
1. **Transcribe** with word timestamps. Use Groq `whisper-large-v3` on the free tier, and first check that word-level
   timestamps are returned. Fall back to local `faster-whisper`.
2. **Cut** silences (`ffmpeg silencedetect`), fillers such as "اممم" and "يعني", and false starts. When a sentence is repeated,
   keep the **last complete take**: an LLM compares the repeated segments in the transcript.
3. **Clean the audio:** denoise, then loudness-normalize to about -14 LUFS.
4. **Caption** in the exact dialect spoken. Words the model is unsure of are highlighted for review before burn-in.
   Render captions with correct Arabic shaping (libass with HarfBuzz, or browser-rendered caption layers as in Reels v1).
5. **Text-based editing:** deleting words in the transcript removes them from the video.
6. **Templates:** at least 4 original ones built from the brand's design tokens. They add title cards, keyword emphasis,
   simple diagrams or lower-thirds, and B-roll or screenshots that appear when the speaker mentions them.
7. **Reframe** horizontal footage to 9:16 by keeping the face centered.
8. **AI cover image** made from the user's own frames.

### C. No footage
Keep Reels v1: photo scenes with TTS voice-over and music.

### Output and limits
- **Output:** 1080x1920 H.264 + AAC MP4, published or scheduled to Instagram Reels and TikTok.
  - TikTok's Content Posting API needs an audit before public posting. Ship "download and post" plus private posting until it passes.
- **Limits:** a maximum input length and size, a processing-time target (60 seconds of raw video edited in under 3 minutes on
  2 vCPU), all heavy work in the worker, raw files kept for N days, and a cost per reel measured and shown on the usage page.

## Workstream 3: AI Media Buyer
Goal: replace most of an agency media buyer's routine for small budgets, safely.

1. **Connect** the Meta ad account (Development-mode testers now; App Review for `ads_management` and `ads_read` later).
   Keep the code ready for TikTok and Snap.
2. **Campaign builder from the strategy:**
   - objective
   - audiences (vertical pack plus discovery answers)
   - budget split and pacing
   - creatives taken from approved posts and reels, with 2 to 3 variants for A/B testing
   - Everything is created **paused**.
3. **Measurement that matters locally:**
   - tracked WhatsApp click links per ad and per post (a redirect endpoint that counts clicks)
   - UTM links
   - optional "how did you hear about us" logging
   - From these: cost per message, cost per lead and ROAS when sales are reported.
4. **Daily optimizer.** Sync insights, then a rules engine detects:
   - losers (high CPL compared with the account's own median)
   - creative fatigue (frequency and falling CTR)
   - pacing problems
   - learning-phase limits

   The LLM writes each recommendation in plain Arabic (pause X, shift Y% to Z, refresh creative, widen audience) with the numbers behind it.
5. **Approval queue.** One tap to approve, reject or edit. An optional auto mode works inside guardrails: maximum daily budget
   change as a %, maximum total spend, and actions it may never take. Every change is logged with a one-click revert.
6. **Weekly report** in Arabic: what was spent, what it brought, what we changed and why, and next week's plan.
   Never show benchmarks we did not measure.
7. Fold this into the Agent: "شوف الإعلانات وقولي أعمل إيه" returns the same recommendations.

## Workstream 4: Make it a business
- **Plans and quotas:** reels per month, posts, ad accounts, brands and seats, enforced through the usage meter.
  Add a founders' price.
- **Billing:** design for Paymob in Egypt and Moyasar or Tap in Saudi Arabia. Ship manual invoicing first if needed.
- **Agency mode:** many brands, client approval links, and roles.
- **Ops:** Alembic migrations, error monitoring, backups, a status page, and rate limits.
- **Legal:** ToS and Privacy Policy that cover Egypt's data law and Saudi PDPL, the content rights of uploads, and music
  licensing (our generated music is ours; user uploads are the user's responsibility).
- Update `DEPLOY.md` for the free stack and the first paid upgrades.

## Order of work and reporting
1. Workstream 0, then a short positioning and pricing decision note for the founders to approve.
2. Workstream 1 design tokens and components, applied while building the next items.
3. Reels Studio v2: script mode and teleprompter, then raw-upload editing, then templates.
4. AI Media Buyer: tracking links and insights sync, then recommendations and approvals, then guarded auto mode.
5. Workstream 4.

After each milestone, report:
- what shipped
- screenshots
- test results
- cost per unit
- known limits
- the decisions you need from the founders

Ask only when a choice is truly the founders'. Otherwise pick the sensible default and say so.
