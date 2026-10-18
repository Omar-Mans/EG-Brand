import type { Job } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "egbrand.token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {}
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown; form?: FormData } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { method: opts.method || (body ? "POST" : "GET"), headers, body });
  } catch {
    throw new ApiError(0, "مش قادرين نوصل للسيرفر. اتأكد إن الـ API شغال.");
  }
  if (res.status === 401 && typeof window !== "undefined" && path !== "/api/auth/login" && path !== "/api/auth/register") {
    setToken(null);
    window.location.href = "/login";
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? "البيانات ناقصة أو غلط" : `خطأ ${res.status}`;
    throw new ApiError(res.status, msg);
  }
  return data as T;
}

const JOB_ERRORS: Record<string, string> = {
  budget_exceeded: "الشركة وصلت لحد ميزانية الـ AI الشهرية.",
  invalid_json: "رد الـ AI رجع بشكل غير متوقع. جرّب تاني.",
  upstream_error: "مزود الـ AI مش متاح دلوقتي. جرّب تاني بعد شوية.",
  no_dna: "ولّد هوية البراند الأول.",
};

/** Polls a background job until it finishes. */
export async function waitJob(job: Job, onTick?: (j: Job) => void, timeoutMs = 300_000): Promise<Job> {
  const started = Date.now();
  let current = job;
  while (current.status === "queued" || current.status === "running") {
    if (Date.now() - started > timeoutMs) throw new ApiError(408, "العملية أخدت وقت أطول من المتوقع. اتأكد إن الـ worker شغال.");
    await new Promise((r) => setTimeout(r, 1500));
    current = await api<Job>(`/api/jobs/${job.id}`);
    onTick?.(current);
  }
  if (current.status === "failed") {
    const code = current.error.split(":")[0];
    throw new ApiError(500, JOB_ERRORS[code] || current.error || "العملية فشلت");
  }
  return current;
}
