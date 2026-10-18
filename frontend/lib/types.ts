export type Brief = {
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

export type Brand = { id: string; name: string; brief: Brief; dna: Dna | null; created_at: string };

export type Layout = "photo_overlay" | "photo_split" | "bold" | "offer" | "minimal" | "quote";

export type PostDesign = {
  subheadline?: string;
  badge?: string;
  layout?: Layout;
  visual_prompt?: string;
  plan?: { local_at: string; platforms: string[] };
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
