"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";

import { ErrorAlert, fmtDate, statusIcon, StatusBadge } from "@/components/common/ui";
import { api } from "@/lib/api";
import { qk } from "@/lib/queries";
import type { Chapter, MaterialDetail } from "@/lib/types";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function PlanForm({ material }: { material: MaterialDetail }) {
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [start, setStart] = useState(material.plan.start && material.plan.start > today ? material.plan.start : today);
  const [target, setTarget] = useState(material.plan.target ?? "");
  const [weekdays, setWeekdays] = useState<number[]>(material.plan.weekdays.length ? material.plan.weekdays : [0, 1, 2, 3, 4, 5, 6]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const generate = async () => {
    setBusy(true);
    setError(null);
    try {
      await api(`/materials/${material.slug}/plan/`, { body: { start_date: start, target_date: target || null, weekdays } });
      await qc.invalidateQueries({ queryKey: qk.material(material.slug) });
      await qc.invalidateQueries({ queryKey: qk.dashboard });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="card mb-3">
      <div className="card-header">
        <h2 className="h6 mb-0">{material.plan_status.has_plan ? "Reschedule the plan" : "Generate a study plan"}</h2>
        <small className="text-secondary">Chapters that are not learned yet are spread over your study days, weighted by page count.</small>
      </div>
      <div className="card-body">
        <ErrorAlert error={error} />
        <div className="row g-3 align-items-end">
          <div className="col-sm-6 col-lg-3">
            <label className="form-label small fw-semibold">Start</label>
            <input type="date" className="form-control" value={start} onChange={(e) => setStart(e.target.value)} />
          </div>
          <div className="col-sm-6 col-lg-3">
            <label className="form-label small fw-semibold">Exam / target date (optional)</label>
            <input type="date" className="form-control" value={target} min={start} onChange={(e) => setTarget(e.target.value)} />
          </div>
          <div className="col-lg-4">
            <label className="form-label small fw-semibold d-block">Study days</label>
            <div className="d-flex gap-1">
              {DAYS.map((d, i) => (
                <button
                  key={d}
                  type="button"
                  className="opt"
                  aria-pressed={weekdays.includes(i)}
                  onClick={() => setWeekdays((w) => (w.includes(i) ? w.filter((x) => x !== i) : [...w, i].sort()))}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
          <div className="col-lg-2">
            <button className="btn btn-primary w-100" onClick={generate} disabled={busy || !weekdays.length}>
              <i className="bi bi-calendar-check me-1" />
              {material.plan_status.has_plan ? "Regenerate" : "Generate"}
            </button>
          </div>
        </div>
        {!target && <div className="small text-secondary mt-2">Without a target date the default pace is about 25 pages per study day.</div>}
      </div>
    </div>
  );
}

export function StudyPlan({ material }: { material: MaterialDetail }) {
  const groups = useMemo(() => {
    const out: { title: string; subtitle: string; chapters: Chapter[] }[] = [];
    for (const c of material.chapters) {
      const last = out[out.length - 1];
      if (last && last.title === c.group_title) last.chapters.push(c);
      else out.push({ title: c.group_title, subtitle: c.group_subtitle, chapters: [c] });
    }
    return out;
  }, [material.chapters]);
  const ps = material.plan_status;
  const today = new Date().toISOString().slice(0, 10);

  return (
    <>
      <div className="row g-3 mb-3">
        <div className="col-sm-4">
          <div className="card h-100">
            <div className="card-body kpi">
              <div className="kpi-top">
                <span className="kpi-icon success">
                  <i className="bi bi-check2-circle" />
                </span>
                Learned
              </div>
              <div className="kpi-value">
                {ps.learned} <span className="fs-6 text-secondary fw-normal">/ {ps.total}</span>
              </div>
              <div className="progress" style={{ height: 6 }}>
                <div className="progress-bar bg-success" style={{ width: `${ps.total ? (ps.learned / ps.total) * 100 : 0}%` }} />
              </div>
            </div>
          </div>
        </div>
        <div className="col-sm-4">
          <div className="card h-100">
            <div className="card-body kpi">
              <div className="kpi-top">
                <span className={`kpi-icon ${ps.on_track ? "success" : "warning"}`}>
                  <i className={`bi ${ps.on_track ? "bi-emoji-smile" : "bi-alarm"}`} />
                </span>
                Schedule
              </div>
              <div className="kpi-value">{!ps.has_plan ? "—" : ps.on_track ? "On track" : `${ps.behind} behind`}</div>
              <div className="kpi-sub">{ps.has_plan ? `${ps.scheduled_by_today} chapters planned up to today` : "No plan yet"}</div>
            </div>
          </div>
        </div>
        <div className="col-sm-4">
          <div className="card h-100">
            <div className="card-body kpi">
              <div className="kpi-top">
                <span className="kpi-icon">
                  <i className="bi bi-flag" />
                </span>
                Target
              </div>
              <div className="kpi-value">{material.plan.target ? fmtDate(material.plan.target, { year: "numeric", month: "short", day: "numeric" }) : "—"}</div>
              <div className="kpi-sub">{material.page_count} pages · {material.chapters_total} chapters</div>
            </div>
          </div>
        </div>
      </div>

      <PlanForm material={material} />

      <div className="card overflow-hidden">
        {groups.map((g) => {
          const learned = g.chapters.filter((c) => c.status === "learned").length;
          return (
            <div key={g.title + g.chapters[0].key}>
              <div className="lesson-head">
                <span>{g.title}</span>
                <small className="text-truncate">{g.subtitle}</small>
                <span className="ms-auto small text-secondary">
                  {learned}/{g.chapters.length}
                </span>
              </div>
              {g.chapters.map((c) => {
                const si = statusIcon(c.status);
                const overdue = c.scheduled_date && c.scheduled_date < today && c.status !== "learned";
                return (
                  <Link key={c.key} href={`/chapters/${c.material}/${c.key}`} className="plan-row">
                    <span className={`status-ic badge-soft no-dot ${si.cls}`} title={si.label}>
                      <i className={`bi ${si.icon}`} />
                    </span>
                    <span className="code">{c.key}</span>
                    <span className="flex-grow-1 min-w-0">
                      <span className="d-block text-truncate fw-medium">{c.title}</span>
                      <span className="small text-secondary">
                        pp. {c.start_page}–{c.end_page} · {c.pages} pages
                        {c.has_content ? " · summary ready" : ""}
                      </span>
                    </span>
                    {c.scheduled_date && (
                      <span className={`small ${overdue ? "text-danger fw-semibold" : "text-secondary"}`} title="Planned date">
                        <i className="bi bi-calendar3 me-1" />
                        {fmtDate(c.scheduled_date)}
                      </span>
                    )}
                    <span className="d-none d-md-inline">
                      <StatusBadge status={c.status} />
                    </span>
                  </Link>
                );
              })}
            </div>
          );
        })}
        {!groups.length && <div className="empty-state">Import a PDF to build the chapters.</div>}
      </div>
    </>
  );
}
