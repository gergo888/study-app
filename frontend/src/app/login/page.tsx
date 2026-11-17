"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/login/", { body: { password } });
      const next = params.get("next");
      router.replace(next && next.startsWith("/") && !next.startsWith("//") ? next : "/");
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? "Too many attempts. Wait a minute." : err instanceof Error ? err.message : "Login failed");
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="card auth-card">
        <div className="card-body p-4">
          <div className="d-flex align-items-center gap-2 mb-4">
            <span className="brand-mark">
              <i className="bi bi-mortarboard-fill" />
            </span>
            <span className="fw-bold fs-5">StudyDesk</span>
          </div>
          <h1 className="h5 mb-1">Welcome back</h1>
          <p className="text-secondary small mb-4">Enter your password to continue studying.</p>
          <form onSubmit={submit}>
            <label className="form-label small fw-semibold" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className={`form-control mb-3 ${error ? "is-invalid" : ""}`}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
              autoComplete="current-password"
              required
            />
            {error && <div className="text-danger small mb-3">{error}</div>}
            <button className="btn btn-primary w-100" disabled={busy || !password}>
              {busy ? <span className="spinner-border spinner-border-sm" /> : "Log in"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
