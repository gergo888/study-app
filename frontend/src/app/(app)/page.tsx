"use client";

import Link from "next/link";

import { ErrorAlert, fmtDate, Loader, StatusBadge } from "@/components/common/ui";
import { useDashboard } from "@/lib/queries";

const KIND_LABEL: Record<string, string> = { flashcard: "Flashcard", quiz: "Quiz", reveal: "Revealed", write: "Wrote out" };
const RESULT_COLOR: Record<string, string> = {
  correct: "var(--success)",
  seen: "var(--info)",
  partial: "var(--warning)",
  wrong: "var(--danger)",
};

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function DashboardPage() {
  const { data, error, isLoading } = useDashboard();
  if (isLoading) return <Loader />;
  if (error || !data) return <ErrorAlert error={error} />;
  const maxXp = Math.max(10, ...data.xp_by_day.map((d) => d.xp));

  return (
    <>
      <div className="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
        <div>
          <h1 className="page-title">{greeting()}!</h1>
          <p className="text-secondary mb-0">
            {data.due.total ? `${data.due.total} cards are waiting for review.` : "No reviews due right now."} {data.xp_today ? `You earned ${data.xp_today} XP today.` : ""}
          </p>
        </div>
        <div className="d-flex gap-2">
          <Link href="/review" className={`btn btn-primary ${data.due.total ? "" : "disabled"}`}>
            <i className="bi bi-arrow-repeat me-1" />
            Review due cards
          </Link>
          <Link href="/materials" className="btn btn-outline-primary">
            <i className="bi bi-collection me-1" />
            Materials
          </Link>
        </div>
      </div>

      <div className="row g-3 mb-3">
        <div className="col-6 col-xl-3">
          <div className="card h-100">
            <div className="card-body kpi">
              <div className="kpi-top">
                <span className="kpi-icon warning">
                  <i className="bi bi-stars" />
                </span>
                Level {data.level}
              </div>
              <div className="kpi-value">{data.xp} XP</div>
              <div className="progress mt-1" style={{ height: 6 }}>
                <div className="progress-bar" style={{ width: `${Math.round(data.progress * 100)}%` }} />
              </div>
              <div className="kpi-sub">{data.next_level_at - data.xp} XP to level {data.level + 1}</div>
            </div>
          </div>
        </div>
        <div className="col-6 col-xl-3">
          <div className="card h-100">
            <div className="card-body kpi">
              <div className="kpi-top">
                <span className="kpi-icon info">
                  <i className="bi bi-arrow-repeat" />
                </span>
                Due reviews
              </div>
              <div className="kpi-value">{data.due.total}</div>
              <div className="kpi-sub">
                {data.due.by_kind.flashcard ?? 0} flashcards · {data.due.by_kind.quiz ?? 0} quiz · {data.reviews_today} reviewed today
              </div>
            </div>
          </div>
        </div>
        <div className="col-6 col-xl-3">
          <div className="card h-100">
            <div className="card-body kpi">
              <div className="kpi-top">
                <span className="kpi-icon success">
                  <i className="bi bi-check2-circle" />
                </span>
                Chapters learned
              </div>
              <div className="kpi-value">
                {data.chapters_learned}
                <span className="fs-6 text-secondary fw-normal"> / {data.chapters_total}</span>
              </div>
              <div className="progress mt-1" style={{ height: 6 }}>
                <div className="progress-bar bg-success" style={{ width: `${data.chapters_total ? (data.chapters_learned / data.chapters_total) * 100 : 0}%` }} />
              </div>
            </div>
          </div>
        </div>
        <div className="col-6 col-xl-3">
          <div className="card h-100">
            <div className="card-body kpi">
              <div className="kpi-top">
                <span className="kpi-icon">
                  <i className="bi bi-fire" />
                </span>
                Study streak
              </div>
              <div className="kpi-value">
                {data.streak} <span className="fs-6 text-secondary fw-normal">{data.streak === 1 ? "day" : "days"}</span>
              </div>
              <div className="kpi-sub">Study a little every day to keep it going.</div>
            </div>
          </div>
        </div>
      </div>

      <div className="row g-3">
        <div className="col-xl-8">
          <div className="card mb-3">
            <div className="card-header">
              <h2 className="h6 mb-0">Continue studying</h2>
              <small className="text-secondary">Next chapter of each study plan</small>
            </div>
            <div className="card-body">
              {data.continue.length === 0 && <div className="text-secondary small">Create a study material and import its PDF to get started.</div>}
              {data.continue.map((c) => (
                <Link key={c.material} href={`/chapters/${c.material}/${c.chapter}`} className="d-flex align-items-center gap-3 text-decoration-none text-reset py-2">
                  <span className="doc-icon">
                    <i className="bi bi-journal-text" />
                  </span>
                  <div className="flex-grow-1 min-w-0">
                    <div className="small text-secondary">{c.material_title}</div>
                    <div className="fw-semibold text-truncate">
                      {c.code ? `${c.code} · ` : ""}
                      {c.title}
                    </div>
                    <div className="small text-secondary">
                      {c.learned}/{c.total} learned
                      {c.scheduled_date && ` · planned for ${fmtDate(c.scheduled_date)}`}
                      {c.behind > 0 && <span className="text-danger"> · {c.behind} behind plan</span>}
                    </div>
                  </div>
                  <StatusBadge status={c.status} />
                  <i className="bi bi-chevron-right text-secondary" />
                </Link>
              ))}
            </div>
          </div>
          <div className="card">
            <div className="card-header">
              <h2 className="h6 mb-0">XP in the last 14 days</h2>
            </div>
            <div className="card-body">
              <div className="chart-bars" role="img" aria-label="XP earned per day">
                {data.xp_by_day.map((d) => (
                  <div
                    key={d.date}
                    className={`bar ${d.xp ? "" : "zero"}`}
                    style={{ height: `${(d.xp / maxXp) * 100}%` }}
                    title={`${fmtDate(d.date)}: ${d.xp} XP`}
                  />
                ))}
              </div>
              <div className="chart-labels">
                {data.xp_by_day.map((d, i) => (
                  <span key={d.date}>{i % 2 === 1 ? fmtDate(d.date, { day: "numeric" }) : ""}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="col-xl-4">
          <div className="card h-100">
            <div className="card-header">
              <h2 className="h6 mb-0">Recent activity</h2>
            </div>
            <div className="card-body">
              {data.recent.length === 0 ? (
                <div className="text-secondary small">Nothing yet — your answers will show up here.</div>
              ) : (
                <ul className="timeline">
                  {data.recent.map((a, i) => (
                    <li key={i} style={{ ["--tl" as string]: RESULT_COLOR[a.result] ?? "var(--primary)" }}>
                      <span className="fw-semibold">{KIND_LABEL[a.kind] ?? a.kind}</span> · {a.result}
                      <small>
                        {a.chapter} {a.chapter_title} · {new Date(a.ts).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                      </small>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
