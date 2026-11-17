"use client";

import Link from "next/link";
import { useLayoutEffect, useMemo, useRef, useState } from "react";

import { Bi, ErrorAlert, FigureView, IssueList, Loader } from "@/components/common/ui";
import { RawEditorModal } from "@/components/editor/RawEditorModal";
import { usePrefs } from "@/lib/prefs";
import { useInvalidateChapter, useSummary, useSummaryOp } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import type { ChapterDetail, Section, SummaryPoint } from "@/lib/types";

import { MemorizeBody } from "./MemorizeBody";
import { PointEditor } from "./PointEditor";

type Mode = "read" | "memorize" | "select" | "edit";

const MODES: { id: Mode; label: string; icon: string }[] = [
  { id: "read", label: "Read", icon: "bi-book" },
  { id: "memorize", label: "Memorize", icon: "bi-eye-slash" },
  { id: "select", label: "Select & practice", icon: "bi-check2-square" },
  { id: "edit", label: "Edit", icon: "bi-pencil" },
];

const CHIP_TITLES = { M: "Memorize (reveal / write)", F: "Flashcard", Q: "Quiz" };

// ---- Keeping the reading position when the mode changes -------------------
// Switching modes changes the height of everything (Memorize hides the texts,
// Edit adds controls…), which would make the page jump. Before the change we
// remember the heading/bullet point at the top of the visible area; after the
// new layout is rendered we scroll so it is exactly where it was.

type Anchor = { id: string; top: number };
const GAP = 8; // space kept between the sticky toolbar and the restored element

function captureAnchor(toolbar: HTMLElement | null): Anchor | null {
  if (window.scrollY < 1) return null; // at the top of the page: nothing to keep
  const visibleFrom = toolbar?.getBoundingClientRect().bottom ?? 0;
  for (const el of document.querySelectorAll<HTMLElement>("[data-anchor]")) {
    const r = el.getBoundingClientRect();
    // Must be clearly visible: the element above a restored anchor ends GAP px below the toolbar,
    // and a point scrolled almost out of view (only its last few lines showing) is not what you read.
    if (r.bottom <= visibleFrom + GAP + 6) continue;
    if (r.top < visibleFrom && r.bottom - visibleFrom < 60) continue;
    return { id: el.id, top: r.top };
  }
  return null;
}

function restoreAnchor(anchor: Anchor | null, toolbar: HTMLElement | null) {
  const el = anchor && document.getElementById(anchor.id);
  if (!anchor || !el) return;
  // Same position as before, but never with its title hidden under the sticky toolbar.
  const visibleFrom = toolbar?.getBoundingClientRect().bottom ?? 0;
  const delta = el.getBoundingClientRect().top - Math.max(anchor.top, visibleFrom + GAP);
  if (Math.abs(delta) > 1) window.scrollBy({ top: delta, behavior: "instant" });
}

function ProgressChips({ point }: { point: SummaryPoint }) {
  const mem = point.progress.write ?? point.progress.reveal;
  const chips: [keyof typeof CHIP_TITLES, string | undefined][] = [
    ["M", mem?.result],
    ["F", point.progress.flashcard?.result],
    ["Q", point.progress.quiz?.result],
  ];
  return (
    <div className="chips" aria-label="Progress on this point">
      {chips.map(([label, result]) => (
        <span key={label} className={`chip ${result ?? ""}`} title={`${CHIP_TITLES[label]}: ${result ?? "not yet"}`}>
          {label}
        </span>
      ))}
    </div>
  );
}

function PointRow({
  slug,
  chapterKey,
  point,
  mode,
  selected,
  onToggle,
  onEdit,
  onDelete,
  onMove,
  resetToken,
  onRecorded,
}: {
  slug: string;
  chapterKey: string;
  point: SummaryPoint;
  mode: Mode;
  selected: boolean;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onMove: (dir: "up" | "down") => void;
  resetToken: number;
  onRecorded: (learned: string | null) => void;
}) {
  return (
    <div className={`point ${selected ? "selected" : ""}`} id={`p-${point.key}`} data-anchor>
      {mode === "select" ? (
        <input className="form-check-input mt-1 flex-none" type="checkbox" checked={selected} onChange={onToggle} aria-label={`Select ${point.title_en}`} />
      ) : (
        <span className="point-bullet" />
      )}
      <div className="point-main" onClick={mode === "select" ? onToggle : undefined}>
        <div className="d-flex align-items-start gap-2">
          <Bi en={point.title_en} hu={point.title_hu} className="point-title flex-grow-1" />
          {point.stale && (
            <span className="badge-soft b-warning" title="The linked flashcard / quiz question was written for an older version of this text">
              cards outdated
            </span>
          )}
          {!!point.missing.length && <span className="badge-soft b-danger">no {point.missing.join(" / ")}</span>}
        </div>
        {mode === "memorize" ? (
          <MemorizeBody slug={slug} chapterKey={chapterKey} point={point} resetToken={resetToken} onRecorded={onRecorded} />
        ) : (
          <div className="point-body">
            <Bi en={point.body_en} hu={point.body_hu} md />
            {point.figure && <FigureView figure={point.figure} />}
          </div>
        )}
        {mode === "edit" && (
          <div className="small text-secondary mt-1">
            <i className="bi bi-key me-1" />
            {point.concepts.map((g) => g[0]).join(" · ") || "no concepts"}
          </div>
        )}
      </div>
      {mode === "edit" ? (
        <div className="d-flex gap-1 flex-none">
          <button className="icon-btn" title="Move up" onClick={() => onMove("up")}>
            <i className="bi bi-arrow-up" />
          </button>
          <button className="icon-btn" title="Move down" onClick={() => onMove("down")}>
            <i className="bi bi-arrow-down" />
          </button>
          <button className="icon-btn" title="Edit" onClick={onEdit}>
            <i className="bi bi-pencil" />
          </button>
          <button className="icon-btn text-danger" title="Delete" onClick={onDelete}>
            <i className="bi bi-trash" />
          </button>
        </div>
      ) : (
        <ProgressChips point={point} />
      )}
    </div>
  );
}

export function SummaryTab({ chapter }: { chapter: ChapterDetail }) {
  const slug = chapter.material;
  const chapterKey = chapter.key;
  const { data, isLoading, error } = useSummary(slug, chapterKey);
  const { lang } = usePrefs();
  const op = useSummaryOp(slug, chapterKey);
  const invalidate = useInvalidateChapter();
  const toast = useToast();
  const [mode, setMode] = useState<Mode>("read");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [editing, setEditing] = useState<{ point: SummaryPoint | null; section: string } | null>(null);
  const [raw, setRaw] = useState(false);
  const [resetToken, setResetToken] = useState(0);
  const [opError, setOpError] = useState<unknown>(null);

  const allPoints = useMemo(() => data?.sections.flatMap((s) => s.points) ?? [], [data]);
  const memorized = allPoints.filter((p) => p.progress.reveal || p.progress.write).length;

  const toolbarRef = useRef<HTMLDivElement>(null);
  const anchorRef = useRef<Anchor | null>(null);
  useLayoutEffect(() => {
    restoreAnchor(anchorRef.current, toolbarRef.current);
    anchorRef.current = null;
  }, [mode, resetToken]);
  /** Run a change that re-lays out the summary while keeping the reading position. */
  const keepPosition = (change: () => void) => {
    anchorRef.current = captureAnchor(toolbarRef.current);
    change();
  };

  if (isLoading) return <Loader />;
  if (error || !data) return <ErrorAlert error={error} />;

  if (!data.exists) {
    return (
      <div className="card">
        <div className="empty-state">
          <i className="bi bi-robot" />
          <div className="fw-semibold text-body mb-1">No summary yet for this chapter.</div>
          <div className="mb-3">
            Ask Claude Code to generate it: <code className="cmd">/generate-chapter {slug} {chapterKey}</code>
          </div>
          <button className="btn btn-sm btn-soft" onClick={() => setRaw(true)}>
            <i className="bi bi-markdown me-1" />
            Or write summary.md by hand
          </button>
        </div>
        <RawEditorModal show={raw} onHide={() => setRaw(false)} slug={slug} chapterKey={chapterKey} kind="summary" />
      </div>
    );
  }

  const run = async (body: Record<string, unknown>) => {
    setOpError(null);
    try {
      await op.mutateAsync({ ...body, base_sha: data.sha });
    } catch (e) {
      setOpError(e);
    }
  };

  const onRecorded = (learned: string | null) => {
    invalidate(slug, chapterKey);
    if (learned) toast(`Chapter learned (via ${learned})! 🎉`, "success");
  };

  const toggle = (key: string) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(key)) n.delete(key);
      else n.add(key);
      return n;
    });
  const toggleSection = (s: Section) =>
    setSelected((cur) => {
      const n = new Set(cur);
      const all = s.points.every((p) => n.has(p.key));
      s.points.forEach((p) => (all ? n.delete(p.key) : n.add(p.key)));
      return n;
    });

  const practiceHref = (m: string) => `/practice?mode=${m}&material=${slug}&chapter=${chapterKey}&points=${[...selected].join(",")}`;
  // "has no flashcard/quiz" warnings are shown inline as badges on the points.
  const linkIssues = data.issues.filter((i) => !/has no (flashcard|quiz question)$/.test(i.message));

  return (
    <>
      <div className="summary-toolbar d-flex flex-wrap align-items-center gap-2" ref={toolbarRef}>
        <div className="seg" role="group" aria-label="Summary mode">
          {MODES.map((m) => (
            <button key={m.id} aria-pressed={mode === m.id} onClick={() => m.id !== mode && keepPosition(() => setMode(m.id))}>
              <i className={`bi ${m.icon} me-1`} />
              {m.label}
            </button>
          ))}
        </div>
        {mode === "memorize" && (
          <>
            <span className="small text-secondary ms-2">
              {memorized}/{allPoints.length} points memorized
            </span>
            <button className="btn btn-sm btn-light" onClick={() => keepPosition(() => setResetToken((t) => t + 1))}>
              <i className="bi bi-arrow-counterclockwise me-1" />
              Hide all
            </button>
          </>
        )}
        <div className="ms-auto d-flex gap-2">
          {mode === "edit" && (
            <button className="btn btn-sm btn-light" onClick={() => setRaw(true)}>
              <i className="bi bi-markdown me-1" />
              Edit Markdown
            </button>
          )}
          <Link className="btn btn-sm btn-light" href={`/print/chapters/${slug}/${chapterKey}?lang=${lang}`} target="_blank">
            <i className="bi bi-printer me-1" />
            Print
          </Link>
        </div>
      </div>

      <ErrorAlert error={opError} />
      {mode === "edit" && <IssueList issues={linkIssues} />}

      {data.sections.map((s, si) => {
        const allSel = s.points.length > 0 && s.points.every((p) => selected.has(p.key));
        return (
          <div className="card summary-section" key={s.key}>
            <div className="card-body">
              <div className="d-flex align-items-start gap-2 mb-1" id={`s-${s.key}`} data-anchor>
                {mode === "select" && <input className="form-check-input mt-1" type="checkbox" checked={allSel} onChange={() => toggleSection(s)} aria-label="Select section" />}
                <Bi en={s.heading_en} hu={s.heading_hu} className="section-title flex-grow-1" />
                {mode === "edit" && (
                  <div className="d-flex gap-1">
                    <button className="icon-btn" title="Move section up" disabled={si === 0} onClick={() => run({ op: "move_section", section_key: s.key, direction: "up" })}>
                      <i className="bi bi-arrow-up" />
                    </button>
                    <button className="icon-btn" title="Move section down" disabled={si === data.sections.length - 1} onClick={() => run({ op: "move_section", section_key: s.key, direction: "down" })}>
                      <i className="bi bi-arrow-down" />
                    </button>
                    <button
                      className="icon-btn"
                      title="Rename section"
                      onClick={() => {
                        const en = window.prompt("Section heading (English)", s.heading_en);
                        if (en === null) return;
                        const hu = window.prompt("Section heading (Hungarian)", s.heading_hu);
                        if (hu === null) return;
                        void run({ op: "update_section", section_key: s.key, heading_en: en, heading_hu: hu });
                      }}
                    >
                      <i className="bi bi-pencil" />
                    </button>
                    <button
                      className="icon-btn text-danger"
                      title="Delete section"
                      onClick={() => window.confirm(`Delete section "${s.heading_en}" with its ${s.points.length} points and their cards?`) && run({ op: "delete_section", section_key: s.key })}
                    >
                      <i className="bi bi-trash" />
                    </button>
                  </div>
                )}
              </div>
              {s.points.map((p) => (
                <PointRow
                  key={p.key}
                  slug={slug}
                  chapterKey={chapterKey}
                  point={p}
                  mode={mode}
                  selected={selected.has(p.key)}
                  onToggle={() => toggle(p.key)}
                  onEdit={() => setEditing({ point: p, section: s.key })}
                  onDelete={() => window.confirm(`Delete "${p.title_en}" and its flashcard + quiz question?`) && run({ op: "delete_point", point_key: p.key })}
                  onMove={(direction) => run({ op: "move_point", point_key: p.key, direction })}
                  resetToken={resetToken}
                  onRecorded={onRecorded}
                />
              ))}
              {mode === "edit" && (
                <button className="btn btn-sm btn-soft mt-2" onClick={() => setEditing({ point: null, section: s.key })}>
                  <i className="bi bi-plus-lg me-1" />
                  Add point
                </button>
              )}
            </div>
          </div>
        );
      })}

      {mode === "edit" && (
        <button
          className="btn btn-outline-primary"
          onClick={() => {
            const en = window.prompt("New section heading (English)");
            if (!en) return;
            const hu = window.prompt("Section heading (Hungarian)") ?? "";
            void run({ op: "add_section", heading_en: en, heading_hu: hu || en });
          }}
        >
          <i className="bi bi-plus-lg me-1" />
          Add section
        </button>
      )}

      {mode === "select" && (
        <div className="select-bar">
          <span className="fw-semibold">{selected.size} selected</span>
          <button className="btn btn-sm btn-light" onClick={() => setSelected(new Set(allPoints.map((p) => p.key)))}>
            Select all
          </button>
          <button className="btn btn-sm btn-light" onClick={() => setSelected(new Set())} disabled={!selected.size}>
            Clear
          </button>
          <span className="ms-auto small text-secondary">Practice:</span>
          {(["flashcards", "quiz", "write"] as const).map((m) => (
            <Link key={m} href={practiceHref(m)} className={`btn btn-sm btn-primary ${selected.size ? "" : "disabled"}`}>
              {m === "flashcards" ? "Flashcards" : m === "quiz" ? "Quiz" : "Write out"}
            </Link>
          ))}
        </div>
      )}

      {editing && (
        <PointEditor
          onHide={() => setEditing(null)}
          slug={slug}
          chapterKey={chapterKey}
          point={editing.point}
          sectionKey={editing.section}
          summarySha={data.sha}
        />
      )}
      <RawEditorModal show={raw} onHide={() => setRaw(false)} slug={slug} chapterKey={chapterKey} kind="summary" />
    </>
  );
}

