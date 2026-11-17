// Thin fetch wrapper for the Django API (same origin via Next rewrites / nginx).

import type { Issue } from "./types";

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, data: unknown, message?: string) {
    super(message ?? detailOf(data) ?? `Request failed (${status})`);
    this.status = status;
    this.data = data;
  }
}

function detailOf(data: unknown): string | undefined {
  if (data && typeof data === "object") {
    const d = data as Record<string, unknown>;
    if (typeof d.detail === "string") return d.detail;
    if (d.detail && typeof d.detail === "object") return detailOf(d.detail);
    const first = Object.entries(d)[0];
    if (first && Array.isArray(first[1])) return `${first[0]}: ${first[1].join(" ")}`;
  }
  return undefined;
}

export function issuesOf(err: unknown): Issue[] {
  if (err instanceof ApiError && err.data && typeof err.data === "object") {
    const d = err.data as { issues?: unknown; detail?: { issues?: unknown } };
    const issues = d.issues ?? d.detail?.issues;
    if (Array.isArray(issues)) return issues as Issue[];
  }
  return [];
}

function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
  return m ? decodeURIComponent(m[1]) : null;
}

let csrfPromise: Promise<void> | null = null;
export async function ensureCsrf(): Promise<string> {
  let token = getCookie("csrftoken");
  if (!token) {
    csrfPromise ??= fetch("/api/auth/csrf/", { credentials: "same-origin" }).then(() => undefined);
    await csrfPromise;
    csrfPromise = null;
    token = getCookie("csrftoken");
  }
  return token ?? "";
}

type Options = { method?: string; body?: unknown; form?: FormData; signal?: AbortSignal };

export async function api<T = unknown>(path: string, opts: Options = {}): Promise<T> {
  const method = opts.method ?? (opts.body !== undefined || opts.form ? "POST" : "GET");
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") headers["X-CSRFToken"] = await ensureCsrf();
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  const res = await fetch(`/api${path}`, { method, headers, body, credentials: "same-origin", signal: opts.signal });
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (res.status === 401 && typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    const next = window.location.pathname + window.location.search;
    // Outside React (no router here): a full navigation also clears all cached data.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- intentional hard reload
    window.location.assign(`/login?next=${encodeURIComponent(next)}`);
  }
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

/** Upload with progress (XHR) — used for big PDFs. */
export async function upload<T>(path: string, form: FormData, onProgress: (pct: number) => void): Promise<T> {
  const token = await ensureCsrf();
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api${path}`);
    xhr.withCredentials = true;
    xhr.setRequestHeader("X-CSRFToken", token);
    xhr.setRequestHeader("Accept", "application/json");
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => {
      let data: unknown = null;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        data = xhr.responseText;
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data as T);
      else reject(new ApiError(xhr.status, data));
    };
    xhr.onerror = () => reject(new ApiError(0, null, "Network error"));
    xhr.send(form);
  });
}
