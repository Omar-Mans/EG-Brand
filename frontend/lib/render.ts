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

type PostLike = Pick<Post, "format" | "headline" | "cta" | "occasion"> & { design?: Post["design"]; bg_url?: string | null };

const imgCache: Record<string, Promise<HTMLImageElement | null>> = {};
function loadImage(url: string): Promise<HTMLImageElement | null> {
  if (!imgCache[url]) {
    imgCache[url] = new Promise((resolve) => {
      const img = new Image();
      img.crossOrigin = "anonymous"; // keeps the canvas exportable
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = url;
    });
  }
  return imgCache[url];
}

function rgba(hex: string, a: number) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function drawCover(ctx: CanvasRenderingContext2D, img: HTMLImageElement, x: number, y: number, w: number, h: number) {
  const s = Math.max(w / img.width, h / img.height);
  const iw = img.width * s, ih = img.height * s;
  ctx.save();
  ctx.beginPath();
  ctx.rect(x, y, w, h);
  ctx.clip();
  ctx.drawImage(img, x + (w - iw) / 2, y + (h - ih) / 2, iw, ih);
  ctx.restore();
}

/** Headline + subheadline + CTA as one block. Returns the block height; draws when `draw` is true. */
function textBlock(ctx: CanvasRenderingContext2D, o: {
  x: number; y: number; w: number; align: CanvasTextAlign; head: string; sub?: string; cta?: string;
  headFam: string; headMax: number; headLines?: number; fg: string; subFg: string; ctaBg?: string; ctaFg?: string;
  ctaOutline?: boolean; draw: boolean;
}) {
  let size = o.headMax, lines: string[] = [];
  for (;;) {
    setFont(ctx, 700, size, o.headFam);
    lines = wrap(ctx, o.head, o.w);
    if (lines.length <= (o.headLines || 3) || size <= 48) break;
    size -= 4;
  }
  const lh = size * 1.22;
  const subSize = Math.round(Math.max(30, size * 0.38));
  setFont(ctx, 500, subSize, "IBM Plex Sans Arabic");
  const subLines = o.sub ? wrap(ctx, o.sub, o.w).slice(0, 2) : [];
  const subLh = subSize * 1.45;
  const ctaH = o.cta ? 84 : 0;
  const gap1 = subLines.length ? size * 0.28 : 0, gap2 = o.cta ? size * 0.42 : 0;
  const total = lines.length * lh + gap1 + subLines.length * subLh + gap2 + ctaH;
  if (!o.draw) return total;
  ctx.textAlign = o.align;
  ctx.textBaseline = "middle";
  let y = o.y + lh / 2;
  const ax = o.align === "center" ? o.x + o.w / 2 : o.align === "right" ? o.x + o.w : o.x;
  setFont(ctx, 700, size, o.headFam);
  ctx.fillStyle = o.fg;
  lines.forEach((l) => { ctx.fillText(l, ax, y); y += lh; });
  y += gap1 - lh / 2 + subLh / 2;
  setFont(ctx, 500, subSize, "IBM Plex Sans Arabic");
  ctx.fillStyle = o.subFg;
  subLines.forEach((l) => { ctx.fillText(l, ax, y); y += subLh; });
  if (o.cta) {
    y += gap2 - subLh / 2;
    setFont(ctx, 700, 38, "IBM Plex Sans Arabic");
    const tw = ctx.measureText(o.cta).width + 88;
    const bx = o.align === "center" ? ax - tw / 2 : o.align === "right" ? ax - tw : ax;
    rrect(ctx, bx, y, tw, ctaH, ctaH / 2);
    if (o.ctaOutline) { ctx.strokeStyle = o.ctaBg || o.fg; ctx.lineWidth = 4; ctx.stroke(); }
    else { ctx.fillStyle = o.ctaBg || o.fg; ctx.fill(); }
    ctx.fillStyle = o.ctaFg || o.fg;
    ctx.textAlign = "center";
    ctx.fillText(o.cta, bx + tw / 2, y + ctaH / 2 + 2);
  }
  return total;
}

function brandMark(ctx: CanvasRenderingContext2D, dna: Dna, x: number, y: number, color: string, align: "right" | "center" = "right", size = 44) {
  const n = nameOf(dna);
  setFont(ctx, 700, size, dna.font_ar);
  ctx.textBaseline = "middle";
  const tw = ctx.measureText(n.ar).width;
  const icon = size * 1.15, gap = 14;
  const total = tw + gap + icon;
  const right = align === "right" ? x : x + total / 2;
  drawIcon(ctx, dna.icon, right - icon / 2, y, icon, color, 8);
  ctx.fillStyle = color;
  ctx.textAlign = "right";
  ctx.fillText(n.ar, right - icon - gap, y + 2);
}

function badge(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, bg: string, fg: string, size = 40) {
  setFont(ctx, 800, size, "IBM Plex Sans Arabic");
  const tw = ctx.measureText(text).width + size * 1.4, h = size * 1.9;
  rrect(ctx, x, y, tw, h, h / 2);
  ctx.fillStyle = bg;
  ctx.fill();
  ctx.fillStyle = fg;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, x + tw / 2, y + h / 2 + 2);
}

/** Draws a finished post design. Text is real Arabic type over an optional background photo. */
export async function drawPost(cv: HTMLCanvasElement, dna: Dna, post: PostLike) {
  const W = 1080, H = post.format === "post" ? 1080 : 1920, tall = H > W;
  cv.width = W;
  cv.height = H;
  const ctx = cv.getContext("2d")!;
  const p = palette(dna);
  const d = post.design || {};
  await ensureFont(dna.font_ar, post.headline + nameOf(dna).ar);
  await ensureFont("IBM Plex Sans Arabic", "نص عربي");
  const img = post.bg_url ? await loadImage(post.bg_url) : null;
  let layout = d.layout || "bold";
  if ((layout === "photo_overlay" || layout === "photo_split") && !img) layout = "bold";
  const M = 80, badgeText = d.badge || "", sub = d.subheadline || "";
  ctx.direction = "rtl";

  if (layout === "photo_overlay") {
    drawCover(ctx, img!, 0, 0, W, H);
    let g = ctx.createLinearGradient(0, H * 0.3, 0, H);
    g.addColorStop(0, rgba(p.dark, 0));
    g.addColorStop(0.55, rgba(p.dark, 0.72));
    g.addColorStop(1, rgba(p.dark, 0.94));
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    g = ctx.createLinearGradient(0, 0, 0, 240);
    g.addColorStop(0, rgba(p.dark, 0.55)); g.addColorStop(1, rgba(p.dark, 0));
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, 240);
    brandMark(ctx, dna, W - M, M + 10, p.light);
    if (badgeText) badge(ctx, badgeText, M, M - 24, p.accent, onColor(p.accent, p.dark, p.light));
    else if (post.occasion) badge(ctx, post.occasion, M, M - 24, rgba(p.light, 0.92), p.dark, 34);
    const block = { x: M, w: W - 2 * M, align: "right" as CanvasTextAlign, head: post.headline, sub, cta: post.cta, headFam: dna.font_ar,
      headMax: tall ? 120 : 96, fg: p.light, subFg: rgba(p.light, 0.86), ctaBg: p.accent, ctaFg: onColor(p.accent, p.dark, p.light) };
    const h = textBlock(ctx, { ...block, y: 0, draw: false });
    ctx.fillStyle = p.accent; ctx.fillRect(W - M - 90, H - M - h - 34, 90, 8);
    textBlock(ctx, { ...block, y: H - M - h, draw: true });
  } else if (layout === "photo_split") {
    const ph = Math.round(H * (tall ? 0.58 : 0.56));
    drawCover(ctx, img!, 0, 0, W, ph);
    ctx.fillStyle = p.primary; ctx.fillRect(0, ph, W, H - ph);
    ctx.fillStyle = p.accent; ctx.fillRect(0, ph, W, 10);
    const fg = onColor(p.primary, p.dark, p.light);
    rrect(ctx, W - M - 330, M - 24, 330, 84, 42); ctx.fillStyle = rgba(p.dark, 0.55); ctx.fill();
    brandMark(ctx, dna, W - M - 28, M + 18, p.light, "right", 38);
    if (badgeText) badge(ctx, badgeText, M, M - 24, p.accent, onColor(p.accent, p.dark, p.light));
    const block = { x: M, w: W - 2 * M, align: "right" as CanvasTextAlign, head: post.headline, sub, cta: post.cta, headFam: dna.font_ar,
      headMax: tall ? 104 : 80, headLines: 2, fg, subFg: rgba(fg === p.light ? p.light : p.dark, 0.82), ctaBg: p.dark, ctaFg: p.light };
    const h = textBlock(ctx, { ...block, y: 0, draw: false });
    textBlock(ctx, { ...block, y: ph + (H - ph - h) / 2 + 6, draw: true });
  } else if (layout === "offer") {
    ctx.fillStyle = p.dark; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = p.primary;
    ctx.beginPath(); ctx.moveTo(W, 0); ctx.lineTo(W, H * 0.34); ctx.lineTo(W * 0.55, 0); ctx.closePath(); ctx.fill();
    ctx.beginPath(); ctx.moveTo(0, H); ctx.lineTo(0, H * 0.72); ctx.lineTo(W * 0.38, H); ctx.closePath(); ctx.fill();
    const r = tall ? 250 : 190, cx = W / 2, cy = tall ? 560 : 330;
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fillStyle = p.accent; ctx.fill();
    ctx.beginPath(); ctx.arc(cx, cy, r - 18, 0, Math.PI * 2); ctx.strokeStyle = rgba(onColor(p.accent, p.dark, p.light), 0.35); ctx.lineWidth = 4; ctx.stroke();
    const bt = badgeText || "عرض خاص";
    ctx.fillStyle = onColor(p.accent, p.dark, p.light); ctx.textAlign = "center"; ctx.textBaseline = "middle";
    fit(ctx, bt, 800, tall ? 118 : 92, dna.font_ar, r * 1.6, 40); ctx.fillText(bt, cx, cy + 4);
    const block = { x: M, w: W - 2 * M, align: "center" as CanvasTextAlign, head: post.headline, sub, cta: post.cta, headFam: dna.font_ar,
      headMax: tall ? 104 : 78, headLines: 2, fg: p.light, subFg: rgba(p.light, 0.8), ctaBg: p.accent, ctaFg: onColor(p.accent, p.dark, p.light) };
    const top = cy + r + (tall ? 90 : 50);
    textBlock(ctx, { ...block, y: top, draw: true });
    brandMark(ctx, dna, W / 2, H - 70, p.light, "center", 36);
  } else if (layout === "minimal") {
    ctx.fillStyle = p.light; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = p.primary; ctx.lineWidth = 3; rrect(ctx, 44, 44, W - 88, H - 88, 8); ctx.stroke();
    drawIcon(ctx, dna.icon, W / 2, tall ? 260 : 190, 90, p.primary, 6);
    if (badgeText) { setFont(ctx, 700, 30, "IBM Plex Sans Arabic"); ctx.fillStyle = p.primary; ctx.textAlign = "center"; ctx.fillText(badgeText, W / 2, tall ? 360 : 268); }
    const block = { x: M + 40, w: W - 2 * M - 80, align: "center" as CanvasTextAlign, head: post.headline, sub, cta: post.cta, headFam: dna.font_ar,
      headMax: tall ? 110 : 86, fg: p.dark, subFg: rgba(p.dark, 0.66), ctaBg: p.primary, ctaFg: p.primary, ctaOutline: true };
    const h = textBlock(ctx, { ...block, y: 0, draw: false });
    textBlock(ctx, { ...block, y: (H - h) / 2 + 20, draw: true });
    brandMark(ctx, dna, W / 2, H - 110, p.dark, "center", 34);
  } else if (layout === "quote") {
    ctx.fillStyle = p.light; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = rgba(p.primary, 0.08); ctx.fillRect(0, 0, W, H * 0.5);
    setFont(ctx, 700, 420, "Amiri"); ctx.fillStyle = p.accent; ctx.textAlign = "right"; ctx.textBaseline = "alphabetic";
    ctx.fillText("”", W - M + 20, tall ? 560 : 400);
    const block = { x: M, w: W - 2 * M, align: "right" as CanvasTextAlign, head: post.headline, sub: sub || "من عملائنا", headFam: dna.font_ar,
      headMax: tall ? 96 : 76, headLines: 4, fg: p.dark, subFg: p.primary };
    const h = textBlock(ctx, { ...block, y: 0, draw: false });
    textBlock(ctx, { ...block, y: (H - h) / 2 + (tall ? 80 : 50), draw: true });
    for (let i = 0; i < 5; i++) drawIcon(ctx, "spark", W - M - 22 - i * 52, H - M - 150, 40, p.accent, 9);
    brandMark(ctx, dna, W - M, H - M - 40, p.dark, "right", 36);
  } else {
    // bold
    ctx.fillStyle = p.primary; ctx.fillRect(0, 0, W, H);
    const fg = onColor(p.primary, p.dark, p.light);
    ctx.globalAlpha = 0.12; drawIcon(ctx, dna.icon, W * 0.2, H - W * 0.2, W * 0.62, fg, 5); ctx.globalAlpha = 1;
    ctx.fillStyle = p.accent === p.primary ? fg : p.accent;
    ctx.beginPath(); ctx.moveTo(W, 0); ctx.lineTo(W, 150); ctx.lineTo(W - 150, 0); ctx.closePath(); ctx.fill();
    brandMark(ctx, dna, W - M, M + 10, fg);
    if (badgeText || post.occasion) badge(ctx, badgeText || post.occasion, M, M - 24, fg, p.primary, 36);
    const block = { x: M, w: W - 2 * M, align: "right" as CanvasTextAlign, head: post.headline, sub, cta: post.cta, headFam: dna.font_ar,
      headMax: tall ? 140 : 112, fg, subFg: rgba(fg === p.light ? p.light : p.dark, 0.85), ctaBg: fg, ctaFg: p.primary };
    const h = textBlock(ctx, { ...block, y: 0, draw: false });
    const y = (H - h) / 2 + 10;
    ctx.fillStyle = p.accent === p.primary ? fg : p.accent; ctx.fillRect(W - M - 120, y - 36, 120, 10);
    textBlock(ctx, { ...block, y, draw: true });
  }
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

/* ---------- Reels: one transparent text layer per scene + an opaque outro card (1080x1920). ----------
   ffmpeg moves the photo and fades these layers in, so the Arabic text is always drawn by the browser. */

export type ReelSceneLike = { text: string; sub?: string; bg_url?: string | null };
const RW = 1080, RH = 1920;

/** Words on solid rounded boxes, line by line, like modern reel captions. Returns the bottom y. */
function captionBoxes(ctx: CanvasRenderingContext2D, text: string, cy: number, size: number, fam: string, bg: string, fg: string) {
  setFont(ctx, 800, size, fam);
  let lines = wrap(ctx, text, RW - 260);
  while (lines.length > 3 && size > 64) { size -= 6; setFont(ctx, 800, size, fam); lines = wrap(ctx, text, RW - 260); }
  const lh = size * 1.42, padX = size * 0.42;
  let y = cy - (lines.length * lh) / 2;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  lines.forEach((l) => {
    const w = ctx.measureText(l).width + padX * 2;
    ctx.save();
    ctx.shadowColor = "rgba(0,0,0,.28)"; ctx.shadowBlur = 24; ctx.shadowOffsetY = 8;
    rrect(ctx, RW / 2 - w / 2, y + 6, w, lh - 12, size * 0.28);
    ctx.fillStyle = bg; ctx.fill();
    ctx.restore();
    ctx.fillStyle = fg;
    ctx.fillText(l, RW / 2, y + lh / 2 + 2);
    y += lh;
  });
  return y;
}

/** Subtitle of the spoken line, low in the frame but above the platform's caption area. */
function subtitle(ctx: CanvasRenderingContext2D, text: string) {
  setFont(ctx, 700, 50, "IBM Plex Sans Arabic");
  const lines = wrap(ctx, text, RW - 220).slice(0, 3);
  const lh = 70, top = 1330 - (lines.length - 1) * lh;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  lines.forEach((l, i) => {
    const w = ctx.measureText(l).width + 44;
    rrect(ctx, RW / 2 - w / 2, top + i * lh - lh / 2 + 6, w, lh - 10, 14);
    ctx.fillStyle = "rgba(0,0,0,.55)"; ctx.fill();
    ctx.fillStyle = "#FFFFFF"; ctx.fillText(l, RW / 2, top + i * lh + 2);
  });
}

export async function drawReelScene(cv: HTMLCanvasElement, dna: Dna, scene: ReelSceneLike, index: number, total: number, withPhoto = false,
  caption = "") {
  cv.width = RW; cv.height = RH;
  const ctx = cv.getContext("2d")!;
  const p = palette(dna);
  await ensureFont(dna.font_ar, scene.text + nameOf(dna).ar);
  await ensureFont("IBM Plex Sans Arabic", scene.sub || "نص");
  ctx.clearRect(0, 0, RW, RH);
  ctx.direction = "rtl";
  if (withPhoto) { // preview only: the real video gets the moving photo from ffmpeg
    const img = scene.bg_url ? await loadImage(scene.bg_url) : null;
    if (img) drawCover(ctx, img, 0, 0, RW, RH);
    else { ctx.fillStyle = p.dark; ctx.fillRect(0, 0, RW, RH); }
  }
  // soft shade top and bottom so white text and the platform's own buttons stay readable on any photo
  let g = ctx.createLinearGradient(0, 0, 0, 420);
  g.addColorStop(0, rgba(p.dark, 0.55)); g.addColorStop(1, rgba(p.dark, 0));
  ctx.fillStyle = g; ctx.fillRect(0, 0, RW, 420);
  g = ctx.createLinearGradient(0, RH * 0.45, 0, RH);
  g.addColorStop(0, rgba(p.dark, 0)); g.addColorStop(1, rgba(p.dark, 0.75));
  ctx.fillStyle = g; ctx.fillRect(0, RH * 0.45, RW, RH * 0.55);

  brandMark(ctx, dna, RW / 2, 190, "#FFFFFF", "center", 40);
  const hook = index === 0;
  const boxBg = hook ? p.accent : p.primary;
  const y = caption ? (hook ? RH * 0.4 : RH * 0.48) : (hook ? RH * 0.46 : RH * 0.6);
  const bottom = captionBoxes(ctx, scene.text, y, hook ? 104 : 88, dna.font_ar, boxBg, onColor(boxBg, p.dark, "#FFFFFF"));
  if (scene.sub) {
    setFont(ctx, 600, 46, "IBM Plex Sans Arabic");
    ctx.fillStyle = "#FFFFFF"; ctx.textAlign = "center";
    ctx.save(); ctx.shadowColor = "rgba(0,0,0,.6)"; ctx.shadowBlur = 18;
    wrap(ctx, scene.sub, RW - 280).slice(0, 2).forEach((l, i) => ctx.fillText(l, RW / 2, bottom + 50 + i * 64));
    ctx.restore();
  }
  // progress dots: where we are in the story
  const dot = 14, gap = 14, w = total * dot + (total - 1) * gap;
  for (let i = 0; i < total; i++) {
    ctx.beginPath();
    ctx.arc(RW / 2 + w / 2 - dot / 2 - i * (dot + gap), 268, dot / 2, 0, Math.PI * 2);
    ctx.fillStyle = i === index ? "#FFFFFF" : "rgba(255,255,255,.4)"; ctx.fill();
  }
  if (caption) subtitle(ctx, caption);
}

export async function drawReelOutro(cv: HTMLCanvasElement, dna: Dna, cta: string) {
  cv.width = RW; cv.height = RH;
  const ctx = cv.getContext("2d")!;
  const p = palette(dna), n = nameOf(dna);
  await ensureFont(dna.font_ar, n.ar + cta);
  await ensureFont(dna.font_en, n.en);
  const g = ctx.createLinearGradient(0, 0, RW, RH);
  g.addColorStop(0, p.primary); g.addColorStop(1, p.dark);
  ctx.fillStyle = g; ctx.fillRect(0, 0, RW, RH);
  const fg = onColor(p.primary, p.dark, "#FFFFFF");
  ctx.direction = "rtl"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  rrect(ctx, RW / 2 - 130, 560, 260, 260, 64); ctx.fillStyle = rgba("#FFFFFF", 0.12); ctx.fill();
  drawIcon(ctx, dna.icon, RW / 2, 690, 170, p.accent, 7);
  ctx.fillStyle = fg;
  fit(ctx, n.ar, 800, 132, dna.font_ar, RW - 200); ctx.fillText(n.ar, RW / 2, 960);
  if (dna.tagline_ar) {
    ctx.globalAlpha = 0.85; fit(ctx, dna.tagline_ar, 500, 50, dna.font_ar, RW - 220); ctx.fillText(dna.tagline_ar, RW / 2, 1080); ctx.globalAlpha = 1;
  }
  if (cta) {
    setFont(ctx, 800, 54, "IBM Plex Sans Arabic");
    const tw = Math.min(RW - 200, ctx.measureText(cta).width + 120), h = 120;
    rrect(ctx, RW / 2 - tw / 2, 1210, tw, h, h / 2); ctx.fillStyle = p.accent; ctx.fill();
    ctx.fillStyle = onColor(p.accent, p.dark, "#FFFFFF");
    fit(ctx, cta, 800, 54, "IBM Plex Sans Arabic", tw - 80); ctx.fillText(cta, RW / 2, 1272);
  }
}
