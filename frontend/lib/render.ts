// Draws logos and post designs on canvas with real Arabic web fonts (correct shaping, no AI text artifacts).
import { ICONS } from "./catalog";
import type { Dna, Post } from "./types";

const fontReady: Record<string, Promise<unknown>> = {};
function ensureFont(fam: string, sample: string) {
  if (!fontReady[fam]) {
    fontReady[fam] = Promise.all([
      document.fonts.load(`700 40px "${fam}"`, sample || "نص عربي Abc"),
      document.fonts.load(`400 40px "${fam}"`, sample || "نص عربي Abc"),
    ]).catch(() => null);
  }
  return fontReady[fam];
}

const isHex = (h: string) => /^#[0-9a-f]{6}$/i.test(h || "");
export function palette(dna: Dna) {
  const pick = (role: string, f: string) => {
    const p = (dna.palette || []).find((x) => x.role === role);
    return p && isHex(p.hex) ? p.hex : f;
  };
  return {
    primary: pick("primary", "#C8742B"), secondary: pick("secondary", "#2E4B3C"), accent: pick("accent", "#F2C14E"),
    dark: pick("dark", "#1E1A17"), light: pick("light", "#F6EFE6"),
  };
}
export const nameOf = (dna: Dna) => dna.names?.[dna.chosen || 0] || { ar: "براند", en: "Brand", meaning: "" };

function lum(hex: string) {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
const onColor = (bg: string, dark: string, light: string) => (lum(bg) > 0.45 ? dark : light);

function drawIcon(ctx: CanvasRenderingContext2D, key: string, cx: number, cy: number, size: number, color: string, lw = 7) {
  ctx.save();
  ctx.translate(cx - size / 2, cy - size / 2);
  ctx.scale(size / 100, size / 100);
  ctx.strokeStyle = color;
  ctx.lineWidth = lw;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.stroke(new Path2D(ICONS[key] || ICONS.spark));
  ctx.restore();
}
const setFont = (ctx: CanvasRenderingContext2D, w: number, s: number, fam: string) => {
  ctx.font = `${w} ${s}px "${fam}", "IBM Plex Sans Arabic", sans-serif`;
};
function fit(ctx: CanvasRenderingContext2D, text: string, w: number, size: number, fam: string, maxW: number, min = 24) {
  let s = size;
  setFont(ctx, w, s, fam);
  while (ctx.measureText(text).width > maxW && s > min) setFont(ctx, w, (s -= 2), fam);
}
function wrap(ctx: CanvasRenderingContext2D, text: string, maxW: number) {
  const out: string[] = [];
  String(text || "").split("\n").forEach((par) => {
    let line = "";
    par.split(/\s+/).filter(Boolean).forEach((w) => {
      const t = line ? `${line} ${w}` : w;
      if (ctx.measureText(t).width > maxW && line) {
        out.push(line);
        line = w;
      } else line = t;
    });
    if (line) out.push(line);
  });
  return out;
}
function rrect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, r);
  else ctx.rect(x, y, w, h);
}
function spacing(ctx: CanvasRenderingContext2D, v: string) {
  if ("letterSpacing" in ctx) (ctx as any).letterSpacing = v;
}

export async function drawLogo(cv: HTMLCanvasElement, dna: Dna, variant: number) {
  const W = 800, H = 520;
  cv.width = W;
  cv.height = H;
  const ctx = cv.getContext("2d")!;
  const p = palette(dna), n = nameOf(dna);
  await ensureFont(dna.font_ar, n.ar);
  await ensureFont(dna.font_en, n.en);
  ctx.direction = "rtl";
  ctx.textBaseline = "middle";
  spacing(ctx, "0px");
  if (variant === 0) {
    ctx.fillStyle = p.light; ctx.fillRect(0, 0, W, H);
    rrect(ctx, W / 2 - 75, 50, 150, 150, 36); ctx.fillStyle = p.primary; ctx.fill();
    drawIcon(ctx, dna.icon, W / 2, 125, 104, onColor(p.primary, p.dark, p.light));
    ctx.textAlign = "center"; ctx.fillStyle = p.dark;
    fit(ctx, n.ar, 700, 112, dna.font_ar, W - 120); ctx.fillText(n.ar, W / 2, 316);
    ctx.direction = "ltr"; spacing(ctx, "10px"); setFont(ctx, 600, 32, dna.font_en); ctx.fillStyle = p.primary;
    ctx.fillText((n.en || "").toUpperCase(), W / 2 + 5, 430); spacing(ctx, "0px");
  } else if (variant === 1) {
    ctx.fillStyle = p.dark; ctx.fillRect(0, 0, W, H);
    drawIcon(ctx, dna.icon, W - 150, H / 2, 170, p.accent, 6);
    ctx.textAlign = "right"; ctx.fillStyle = p.light;
    fit(ctx, n.ar, 700, 104, dna.font_ar, W - 320); ctx.fillText(n.ar, W - 270, 205);
    ctx.fillStyle = p.accent; fit(ctx, dna.tagline_ar || "", 400, 36, dna.font_ar, W - 320); ctx.fillText(dna.tagline_ar || "", W - 270, 300);
    ctx.direction = "ltr"; ctx.globalAlpha = 0.7; ctx.fillStyle = p.light; setFont(ctx, 400, 26, dna.font_en);
    ctx.fillText(dna.tagline_en || n.en || "", W - 270, 362); ctx.globalAlpha = 1;
  } else {
    ctx.fillStyle = p.primary; ctx.fillRect(0, 0, W, H);
    const fg = onColor(p.primary, p.dark, p.light);
    ctx.textAlign = "center"; ctx.fillStyle = fg;
    fit(ctx, n.ar, 700, 150, dna.font_ar, W - 100); ctx.fillText(n.ar, W / 2, 220);
    ctx.fillStyle = p.accent === p.primary ? fg : p.accent; rrect(ctx, W / 2 - 50, 318, 100, 8, 4); ctx.fill();
    ctx.direction = "ltr"; spacing(ctx, "12px"); ctx.fillStyle = fg; setFont(ctx, 600, 34, dna.font_en);
    ctx.fillText((n.en || "").toUpperCase(), W / 2 + 6, 392); spacing(ctx, "0px");
  }
}

export async function drawPost(cv: HTMLCanvasElement, dna: Dna, post: Pick<Post, "format" | "template" | "headline" | "cta" | "occasion">) {
  const W = 1080, H = post.format === "post" ? 1080 : 1920;
  cv.width = W;
  cv.height = H;
  const ctx = cv.getContext("2d")!;
  const p = palette(dna), n = nameOf(dna);
  await ensureFont(dna.font_ar, post.headline + n.ar);
  ctx.direction = "rtl";
  ctx.textBaseline = "middle";
  ctx.textAlign = "center";
  const tpl = post.template || 0, padX = 96;
  const [bg, fg, sub] = tpl === 0 ? [p.primary, onColor(p.primary, p.dark, p.light), onColor(p.primary, p.dark, p.light)]
    : tpl === 1 ? [p.dark, p.light, p.accent] : [p.light, p.dark, p.primary];
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
  if (tpl === 0) { ctx.globalAlpha = 0.14; drawIcon(ctx, dna.icon, W * 0.22, H - W * 0.2, W * 0.62, fg, 5); ctx.globalAlpha = 1; }
  if (tpl === 1) { ctx.fillStyle = p.light; ctx.fillRect(0, H * 0.7, W, H * 0.3); ctx.fillStyle = p.accent; ctx.fillRect(0, H * 0.7 - 10, W, 10); }
  if (tpl === 2) { ctx.strokeStyle = p.primary; ctx.lineWidth = 14; rrect(ctx, 48, 48, W - 96, H - 96, 28); ctx.stroke(); drawIcon(ctx, dna.icon, W - 150, 150, 110, p.accent); }
  if (post.occasion) {
    setFont(ctx, 700, 40, dna.font_ar);
    const tw = ctx.measureText(post.occasion).width + 64, top = tpl === 2 ? 230 : 96;
    ctx.fillStyle = tpl === 0 ? fg : p.accent; rrect(ctx, W - padX - tw, top, tw, 74, 37); ctx.fill();
    ctx.fillStyle = tpl === 0 ? bg : p.dark; ctx.fillText(post.occasion, W - padX - tw / 2, top + 38);
  }
  const areaBottom = tpl === 1 ? H * 0.7 : H * 0.8;
  let size = H > W ? 140 : 118, lines: string[];
  for (;;) {
    setFont(ctx, 700, size, dna.font_ar);
    lines = wrap(ctx, post.headline, W - padX * 2);
    if (lines.length <= 3 || size <= 56) break;
    size -= 6;
  }
  const lh = size * 1.3;
  let y = areaBottom / 2 - (lines.length * lh) / 2 + lh / 2;
  ctx.fillStyle = fg;
  lines.forEach((l) => { ctx.fillText(l, W / 2, y); y += lh; });
  if (post.cta) {
    setFont(ctx, 600, 42, "IBM Plex Sans Arabic");
    if (tpl === 1) { ctx.fillStyle = p.dark; ctx.fillText(post.cta, W / 2, H * 0.79); }
    else {
      const tw = ctx.measureText(post.cta).width + 72, cy = y + 40;
      ctx.strokeStyle = sub; ctx.lineWidth = 4; rrect(ctx, W / 2 - tw / 2, cy - 40, tw, 80, 40); ctx.stroke();
      ctx.fillStyle = sub; ctx.fillText(post.cta, W / 2, cy);
    }
  }
  const fy = H - (tpl === 2 ? 130 : 96), footFg = tpl === 1 ? p.dark : fg;
  setFont(ctx, 700, 44, dna.font_ar); ctx.textAlign = "right"; ctx.fillStyle = footFg;
  ctx.fillText(n.ar, W - padX - 70, fy);
  drawIcon(ctx, dna.icon, W - padX - 26, fy, 52, footFg, 8);
}

export function canvasBlob(cv: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => cv.toBlob((b) => (b ? resolve(b) : reject(new Error("render failed"))), "image/png"));
}

export async function downloadCanvas(cv: HTMLCanvasElement, filename: string) {
  const url = URL.createObjectURL(await canvasBlob(cv));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
