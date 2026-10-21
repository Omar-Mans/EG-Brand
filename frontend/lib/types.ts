export type Brief = {
  vertical?: string;
  idea: string;
  name: string;
  market: "EG" | "SA";
  dialect: "egyptian" | "saudi" | "msa";
  styles: string[];
  colors: string[];
  timezone?: string;
};

export type PaletteColor = { role: string; name: string; hex: string };

export type Dna = {
  names: { ar: string; en: string; meaning: string }[];
  chosen: number;
  tagline_ar: string;
  tagline_en: string;
  positioning: string;
  audience: string;
  personality: string[];
  tone: string;
  voice_do: string[];
  voice_dont: string[];
  palette: PaletteColor[];
  font_ar: string;
  font_en: string;
  icon: string;
  pillars: { name: string; share: number }[];
};

export type Brand = {
  id: string; name: string; brief: Brief; dna: Dna | null; created_at: string;
  discovery: Discovery; strategy: Strategy | null;
};

export type Question = { id: string; label: string; type: "text" | "textarea" | "select" | "multi" | "url"; options?: string[]; required?: boolean };
export type Section = { id: string; title: string; questions: Question[] };
export type Answers = Record<string, string | string[]>;
export type Followup = { question: string; why: string; answer: string };
export type Discovery = { answers?: Answers; followups?: Followup[]; website_url?: string; website_text?: string; website_error?: string };

type Kpi = { name: string; target: string; why?: string };
export type Strategy = {
  summary: string; currency: string; created_at: string;
  diagnosis: { strengths: string[]; weaknesses: string[]; opportunities: string[]; threats: string[] };
  positioning: { statement: string; usp: string[]; proof_points: string[] };
  personas: { name: string; age: string; description: string; pains: string[]; motivations: string[]; objections: string[]; where: string[]; message: string }[];
  channels: { platform: string; role: string; priority: "high" | "medium" | "low"; posts_per_week: number; formats: string[]; why: string }[];
  content_pillars: { name: string; share: number; goal: string; examples: string[] }[];
  offers: { title: string; description: string; when: string }[];
  budget: { monthly_total: number; note: string; split: { item: string; pct: number; note: string }[] };
  roadmap: { phase: string; goal: string; actions: string[]; kpis: Kpi[] }[];
  quick_wins: string[]; kpis: Kpi[];
  risks: { risk: string; mitigation: string }[];
  competitors: { name: string; their_strength: string; our_angle: string }[];
};

export type Layout = "photo_overlay" | "photo_split" | "bold" | "offer" | "minimal" | "quote";

export type PostDesign = {
  subheadline?: string;
  badge?: string;
  layout?: Layout;
  visual_prompt?: string;
  photo_query?: string;
  photo_credit?: { name: string; url: string; source: string };
  plan?: { local_at: string; platforms: string[] };
  reel?: Reel;
};

export type ReelScene = {
  text: string; sub: string; voice: string; photo_query?: string; visual_prompt?: string;
  bg_url: string | null; credit?: { name: string; url: string; source: string } | null;
};
export type Reel = {
  voice: string; music: string; music_url?: string | null; scenes: ReelScene[]; outro_voice: string;
  duration?: number; rendered_at?: string;
};

export type PostStatus = "draft" | "scheduled" | "publishing" | "published" | "failed";

export type Post = {
  id: string;
  brand_id: string;
  month: string;
  day: number;
  time: string;
  format: "post" | "reel" | "story";
  pillar: string;
  occasion: string;
  headline: string;
  caption: string;
  hashtags: string[];
  cta: string;
  template: number;
  design: PostDesign;
  bg_url: string | null;
  metrics: Record<string, Record<string, number>>;
  metrics_at: string | null;
  approved: boolean;
  image_url: string | null;
  video_url: string | null;
  status: PostStatus;
  scheduled_at: string | null;
  platforms: string[];
  publish_results: Record<string, { ok: boolean; id?: string; error?: string }>;
  error: string;
};

export type Job = { id: string; kind: string; status: "queued" | "running" | "done" | "failed"; result: any; error: string };

export type Me = {
  id: string;
  email: string;
  name: string;
  is_admin: boolean;
  company: { id: string; name: string; monthly_ai_budget_usd: number };
};

export type SocialAccount = { id: string; provider: string; platform: string; name: string; external_id: string };

export type AdPlan = {
  objective: string;
  budget: number;
  currency: string;
  days: number;
  platforms: string[];
  audience: { age: string; gender: string; locations: string[]; interests: string[] };
  split: { platform: string; pct: number; why: string; amount: number; daily: number }[];
  ads: { platform: string; headline: string; primary_text: string; cta: string }[];
  kpis: string[];
  tips: string[];
};

export type Campaign = {
  id: string;
  brand_id: string;
  objective: string;
  budget: number;
  currency: string;
  days: number;
  platforms: string[];
  plan: AdPlan;
  status: "draft" | "ready" | "created_paused" | "failed";
  external_ids: Record<string, string>;
  error: string;
};

export type Vertical = { id: string; label: string; icon: string; pitch: string };
