"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { usePrefs } from "@/lib/prefs";
import type { ChapterStatus, Figure, Issue } from "@/lib/types";

/** Render Markdown (bodies, notes). `inline` renders paragraphs as spans. */
export function Md({ text, inline = false }: { text: string; inline?: boolean }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={inline ? { p: ({ children }) => <span>{children}</span> } : undefined}
    >
      {text}
    </ReactMarkdown>
  );
}

/** Bilingual text that follows the EN / HU / EN+HU preference. */
export function Bi({
  en,
  hu,
  md = false,
  inline = false,
  as: Tag = "div",
  className,
}: {
  en: string;
  hu: string;
  md?: boolean;
  inline?: boolean;
  as?: "div" | "span";
  className?: string;
}) {
  const { lang } = usePrefs();
  const render = (t: string) => (md ? <Md text={t} inline={inline} /> : t);
  if (lang === "en" || !hu) return <Tag className={className}>{render(en)}</Tag>;
  if (lang === "hu") return <Tag className={className}>{render(hu || en)}</Tag>;
  if (en.trim() === hu.trim()) return <Tag className={className}>{render(en)}</Tag>;
  return (
    <Tag className={className}>
      {render(en)}
      <Tag className="hu-line d-block mt-1">{render(hu)}</Tag>
    </Tag>
  );
}

export function FigureView({ figure, className = "point-figure" }: { figure: Figure; className?: string }) {
  const { lang } = usePrefs();
  const caption = lang === "hu" ? figure.caption_hu : lang === "en" ? figure.caption_en : figure.caption_en === figure.caption_hu ? figure.caption_en : `${figure.caption_en} · ${figure.caption_hu}`;
  return (
    <figure className={className}>
      {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API images, no optimizer */}
      <img src={figure.url} alt={figure.caption_en} loading="lazy" />
      {caption && <figcaption>{caption}</figcaption>}
    </figure>
  );
}

const STATUS: Record<ChapterStatus, { label: string; cls: string; icon: string }> = {
  not_started: { label: "Not started", cls: "b-muted", icon: "bi-circle" },
  reading: { label: "In progress", cls: "b-info", icon: "bi-hourglass-split" },
  read: { label: "Read", cls: "b-warning", icon: "bi-book" },
  learned: { label: "Learned", cls: "b-success", icon: "bi-check-circle-fill" },
};

export function StatusBadge({ status }: { status: ChapterStatus }) {
  const s = STATUS[status];
  return <span className={`badge-soft ${s.cls}`}>{s.label}</span>;
}

export function statusIcon(status: ChapterStatus) {
  return STATUS[status];
}

export function Loader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="d-flex align-items-center gap-2 text-secondary py-4">
      <div className="spinner-border spinner-border-sm text-primary" role="status" />
      {label}
    </div>
  );
}

export function ErrorAlert({ error }: { error: unknown }) {
  if (!error) return null;
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="alert alert-danger d-flex gap-2 align-items-start" role="alert">
      <i className="bi bi-exclamation-triangle" />
      <div>{msg}</div>
    </div>
  );
}

export function IssueList({ issues }: { issues: Issue[] }) {
  if (!issues.length) return null;
  return (
    <ul className="list-unstyled small mb-0">
      {issues.map((i, n) => (
        <li key={n} className={i.severity === "error" ? "text-danger" : "text-warning"}>
          <i className={`bi ${i.severity === "error" ? "bi-x-circle" : "bi-exclamation-circle"} me-1`} />
          <code>
            {i.doc}.md{i.line ? `:${i.line}` : ""}
          </code>{" "}
          {i.message}
        </li>
      ))}
    </ul>
  );
}

export function fmtDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" }) {
  if (!iso) return "";
  const d = iso.length === 10 ? new Date(iso + "T00:00:00") : new Date(iso);
  return d.toLocaleDateString(undefined, opts);
}
