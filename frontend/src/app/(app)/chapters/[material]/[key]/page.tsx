"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Dropdown from "react-bootstrap/Dropdown";

import { ErrorAlert, Loader, StatusBadge } from "@/components/common/ui";
import { CardsTab } from "@/components/flashcards/CardsTab";
import { ChapterNotes } from "@/components/notes/ChapterNotes";
import { SummaryTab } from "@/components/summary/SummaryTab";
import { useChapter, useSetChapterStatus } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import type { ChapterDetail, ChapterStatus } from "@/lib/types";

const STEPS = [
  { id: "read", label: "Read" },
  { id: "summary", label: "Summary" },
  { id: "flashcards", label: "Flashcards" },
  { id: "quiz", label: "Quiz" },
  { id: "notes", label: "Notes" },
] as const;
type Step = (typeof STEPS)[number]["id"];

function stepDone(step: Step, c: ChapterDetail): boolean {
  switch (step) {
    case "read":
      return c.status === "read" || c.status === "learned" || !!c.read_at;
    case "summary":
      return c.has_content && (c.status === "learned" || c.learned_via === "reveal");
    case "flashcards":
      return c.learned_via === "flashcards";
    case "quiz":
      return c.learned_via === "quiz";
    default:
      return false;
  }
}

function ReadStep({ chapter }: { chapter: ChapterDetail }) {
  const setStatus = useSetChapterStatus(chapter.material, chapter.key);
  const router = useRouter();
  const read = chapter.status === "read" || chapter.status === "learned";
  return (
    <>
      <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
        <div className="small text-secondary">
          PDF pages {chapter.start_page}–{chapter.end_page} ({chapter.pages} pages)
        </div>
        <div className="ms-auto d-flex gap-2">
          <a className="btn btn-sm btn-light" href={chapter.pdf_url} target="_blank" rel="noreferrer">
            <i className="bi bi-box-arrow-up-right me-1" />
            Open in new tab
          </a>
          {read ? (
            <button className="btn btn-sm btn-primary" onClick={() => router.replace(`?step=summary`, { scroll: false })}>
              Continue to summary <i className="bi bi-arrow-right ms-1" />
            </button>
          ) : (
            <button
              className="btn btn-sm btn-primary"
              disabled={setStatus.isPending}
              onClick={async () => {
                await setStatus.mutateAsync("read");
                router.replace(`?step=summary`, { scroll: false });
              }}
            >
              <i className="bi bi-check2 me-1" />
              I have read it
            </button>
          )}
        </div>
      </div>
      <iframe className="pdf-frame" src={chapter.pdf_url} title={`PDF: ${chapter.title}`} />
    </>
  );
}

export default function ChapterPage() {
  const { material, key } = useParams<{ material: string; key: string }>();
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { data: chapter, error, isLoading } = useChapter(material, key);
  const setStatus = useSetChapterStatus(material, key);

  if (isLoading) return <Loader />;
  if (error || !chapter) return <ErrorAlert error={error} />;

  const defaultStep: Step = chapter.has_content && chapter.status !== "not_started" ? "summary" : "read";
  const step = (params.get("step") as Step) || defaultStep;
  const go = (s: Step) => router.replace(`/chapters/${material}/${key}?step=${s}`, { scroll: false });
  const changeStatus = async (s: ChapterStatus) => {
    await setStatus.mutateAsync(s);
    toast(s === "learned" ? "Marked as learned" : "Status updated", "success");
  };

  return (
    <>
      <nav className="small mb-2 text-truncate">
        <Link href={`/materials/${material}`} className="text-decoration-none">
          {chapter.material_title}
        </Link>
        <span className="text-secondary">
          {" "}
          / {chapter.group_title}
          {chapter.group_subtitle ? ` · ${chapter.group_subtitle}` : ""}
        </span>
      </nav>
      <div className="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-3">
        <div className="min-w-0">
          <div className="small fw-bold text-primary">{chapter.code || chapter.key}</div>
          <h1 className="page-title">{chapter.title}</h1>
          <div className="d-flex flex-wrap align-items-center gap-2 mt-1 small text-secondary">
            <StatusBadge status={chapter.status} />
            {chapter.learned_via && <span>learned via {chapter.learned_via}</span>}
            {chapter.counts.points > 0 && (
              <span>
                {chapter.counts.points} points · {chapter.counts.flashcards} flashcards · {chapter.counts.quiz} questions
              </span>
            )}
            {chapter.scheduled_date && (
              <span>
                <i className="bi bi-calendar3 me-1" />
                planned {chapter.scheduled_date}
              </span>
            )}
          </div>
        </div>
        <div className="d-flex gap-2">
          <Dropdown align="end">
            <Dropdown.Toggle variant="light" size="sm">
              <i className="bi bi-flag me-1" />
              Progress
            </Dropdown.Toggle>
            <Dropdown.Menu>
              {(["not_started", "reading", "read", "learned"] as ChapterStatus[]).map((s) => (
                <Dropdown.Item key={s} active={chapter.status === s} onClick={() => changeStatus(s)}>
                  {s === "learned" ? "Mark as learned" : s === "read" ? "Mark as read" : s === "reading" ? "In progress" : "Not started"}
                </Dropdown.Item>
              ))}
            </Dropdown.Menu>
          </Dropdown>
          <Link className={`btn btn-sm btn-light ${chapter.prev ? "" : "disabled"}`} href={chapter.prev ? `/chapters/${material}/${chapter.prev}` : "#"} title="Previous chapter">
            <i className="bi bi-chevron-left" />
          </Link>
          <Link className={`btn btn-sm btn-light ${chapter.next ? "" : "disabled"}`} href={chapter.next ? `/chapters/${material}/${chapter.next}` : "#"} title="Next chapter">
            <i className="bi bi-chevron-right" />
          </Link>
        </div>
      </div>

      {(chapter.counts.stale > 0 || chapter.counts.missing > 0) && (
        <div className="alert alert-warning small d-flex gap-2 align-items-start">
          <i className="bi bi-exclamation-triangle mt-1" />
          <div>
            {chapter.counts.stale > 0 && (
              <div>
                <strong>{chapter.counts.stale}</strong> flashcard/quiz item(s) are outdated because their bullet point was edited. Fix them in the Flashcards / Quiz tabs (edit or
                &quot;Still valid&quot;).
              </div>
            )}
            {chapter.counts.missing > 0 && (
              <div>
                <strong>{chapter.counts.missing}</strong> bullet point(s) have no flashcard or quiz question yet.
              </div>
            )}
            <div className="mt-1">
              Or let Claude Code refresh them: <code className="cmd">/generate-chapter --refresh {material} {key}</code>
            </div>
          </div>
        </div>
      )}

      <div className="stepper" role="tablist">
        {STEPS.map((s, i) => {
          const done = stepDone(s.id, chapter);
          return (
            <button key={s.id} role="tab" aria-selected={step === s.id} className={`${step === s.id ? "active" : ""} ${done ? "done" : ""}`} onClick={() => go(s.id)}>
              <span className="num">{done ? <i className="bi bi-check" /> : i + 1}</span>
              {s.label}
            </button>
          );
        })}
      </div>

      {step === "read" && <ReadStep chapter={chapter} />}
      {step === "summary" && <SummaryTab chapter={chapter} />}
      {step === "flashcards" && <CardsTab chapter={chapter} kind="flashcards" />}
      {step === "quiz" && <CardsTab chapter={chapter} kind="quiz" />}
      {step === "notes" && <ChapterNotes slug={material} chapterKey={key} />}
    </>
  );
}
