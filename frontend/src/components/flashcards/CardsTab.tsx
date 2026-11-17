"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import Modal from "react-bootstrap/Modal";

import { Bi, ErrorAlert, FigureView, fmtDate, IssueList, Loader } from "@/components/common/ui";
import {
  figurePayload,
  type FlashcardForm,
  FlashcardFields,
  flashcardForm,
  type QuizForm,
  QuizFields,
  quizForm,
} from "@/components/editor/fields";
import { RawEditorModal } from "@/components/editor/RawEditorModal";
import { api, issuesOf } from "@/lib/api";
import { useCardOp, useFlashcards, useInvalidateChapter, useQuiz, useSummary } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import type { ChapterDetail, Flashcard, QuizQuestion, SrsInfo } from "@/lib/types";

type Kind = "flashcards" | "quiz";

function SrsLine({ srs }: { srs: SrsInfo | null }) {
  if (!srs || !srs.reps) return <span className="small text-secondary">new</span>;
  return (
    <span className="small text-secondary" title="Spaced repetition">
      <i className="bi bi-arrow-repeat me-1" />
      {srs.reps} reviews · due {fmtDate(srs.due)}
    </span>
  );
}

function ItemEditor({
  chapter,
  kind,
  item,
  pointKey,
  sha,
  onHide,
}: {
  chapter: ChapterDetail;
  kind: Kind;
  item: Flashcard | QuizQuestion | null;
  pointKey: string;
  sha: string | null;
  onHide: () => void;
}) {
  const summary = useSummary(chapter.material, chapter.key);
  const op = useCardOp(chapter.material, chapter.key, kind);
  const [point, setPoint] = useState(pointKey);
  const [card, setCard] = useState<FlashcardForm>(flashcardForm((item ?? undefined) as Flashcard | undefined, pointKey));
  const [question, setQuestion] = useState<QuizForm>(quizForm((item ?? undefined) as QuizQuestion | undefined, pointKey));
  const [error, setError] = useState<unknown>(null);
  const points = summary.data?.sections.flatMap((s) => s.points) ?? [];

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const value = kind === "flashcards" ? card : question;
    try {
      await op.mutateAsync({ op: "upsert", base_sha: sha, item: { ...value, point_key: point, figure: figurePayload(value.figure) } });
      onHide();
    } catch (err) {
      setError(err);
    }
  };

  return (
    <Modal show onHide={onHide} size="xl" centered backdrop="static" scrollable>
      <form onSubmit={save} className="d-contents">
        <Modal.Header closeButton>
          <Modal.Title className="h5">
            {item ? "Edit" : "New"} {kind === "flashcards" ? "flashcard" : "quiz question"}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <ErrorAlert error={error} />
          <IssueList issues={issuesOf(error)} />
          {!item && (
            <div className="mb-3">
              <label className="form-label small fw-semibold">Bullet point</label>
              <select className="form-select" value={point} onChange={(e) => setPoint(e.target.value)} required>
                <option value="">Choose…</option>
                {points.map((p) => (
                  <option key={p.key} value={p.key}>
                    {p.title_en}
                  </option>
                ))}
              </select>
            </div>
          )}
          {kind === "flashcards" ? (
            <FlashcardFields slug={chapter.material} chapterKey={chapter.key} value={card} onChange={setCard} />
          ) : (
            <QuizFields slug={chapter.material} chapterKey={chapter.key} value={question} onChange={setQuestion} />
          )}
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-light" onClick={onHide}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={op.isPending || !point}>
            Save
          </button>
        </Modal.Footer>
      </form>
    </Modal>
  );
}

export function CardsTab({ chapter, kind }: { chapter: ChapterDetail; kind: Kind }) {
  const slug = chapter.material;
  const flashcards = useFlashcards(slug, chapter.key);
  const quiz = useQuiz(slug, chapter.key);
  const summary = useSummary(slug, chapter.key);
  const op = useCardOp(slug, chapter.key, kind);
  const invalidate = useInvalidateChapter();
  const toast = useToast();
  const [editing, setEditing] = useState<{ item: Flashcard | QuizQuestion | null; pointKey: string } | null>(null);
  const [raw, setRaw] = useState(false);
  const [opError, setOpError] = useState<unknown>(null);

  const query = kind === "flashcards" ? flashcards : quiz;
  const titles = useMemo(() => {
    const m: Record<string, { en: string; hu: string }> = {};
    summary.data?.sections.forEach((s) => s.points.forEach((p) => (m[p.key] = { en: p.title_en, hu: p.title_hu })));
    return m;
  }, [summary.data]);

  if (query.isLoading) return <Loader />;
  if (query.error || !query.data) return <ErrorAlert error={query.error} />;
  const data = query.data;
  const cardKind = kind === "flashcards" ? "flashcard" : "quiz";
  const stale = (data.items as (Flashcard | QuizQuestion)[]).filter((i) => i.stale).length;

  const confirm = async (key: string) => {
    await api(`/chapters/${slug}/${chapter.key}/cards/confirm/`, { body: { kind: cardKind, card_key: key } });
    invalidate(slug, chapter.key);
    toast("Marked as still valid", "success");
  };
  const remove = async (key: string) => {
    if (!window.confirm("Delete this item? Its review history is kept but it will no longer be practised.")) return;
    setOpError(null);
    try {
      await op.mutateAsync({ op: "delete", key, base_sha: data.sha });
    } catch (e) {
      setOpError(e);
    }
  };

  return (
    <>
      <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
        <div className="small text-secondary">
          {data.items.length} {kind === "flashcards" ? "flashcards" : "questions"}
          {stale > 0 && <span className="text-warning fw-semibold"> · {stale} outdated</span>}
        </div>
        <div className="ms-auto d-flex gap-2">
          <button className="btn btn-sm btn-light" onClick={() => setRaw(true)}>
            <i className="bi bi-markdown me-1" />
            Edit Markdown
          </button>
          <button className="btn btn-sm btn-soft" onClick={() => setEditing({ item: null, pointKey: "" })} disabled={!summary.data?.exists}>
            <i className="bi bi-plus-lg me-1" />
            Add
          </button>
          <Link
            href={`/practice?mode=${kind}&material=${slug}&chapter=${chapter.key}`}
            className={`btn btn-sm btn-primary ${data.items.length ? "" : "disabled"}`}
          >
            <i className="bi bi-play-fill me-1" />
            Practice all
          </Link>
        </div>
      </div>
      <ErrorAlert error={opError} />
      <IssueList issues={data.issues} />
      {!data.exists && (
        <div className="card">
          <div className="empty-state">
            <i className="bi bi-robot" />
            Not generated yet. Run <code className="cmd">/generate-chapter {slug} {chapter.key}</code> in Claude Code.
          </div>
        </div>
      )}
      <div className="row g-3">
        {kind === "flashcards"
          ? (data.items as Flashcard[]).map((c) => (
              <div className="col-lg-6" key={c.key}>
                <div className="card h-100">
                  <div className="card-body d-flex flex-column gap-2">
                    <div className="d-flex align-items-center gap-2 small">
                      <span className="text-secondary text-truncate flex-grow-1">
                        <i className="bi bi-dot" />
                        {titles[c.point_key] ? <Bi as="span" en={titles[c.point_key].en} hu={titles[c.point_key].hu} /> : c.point_key}
                      </span>
                      {c.stale && <span className="badge-soft b-warning">outdated</span>}
                    </div>
                    <Bi en={c.front_en} hu={c.front_hu} md className="fw-semibold" />
                    <div className="border-top pt-2">
                      <Bi en={c.back_en} hu={c.back_hu} md />
                    </div>
                    {c.figure && <FigureView figure={c.figure} />}
                    <div className="d-flex align-items-center gap-1 mt-auto">
                      <SrsLine srs={c.srs} />
                      <span className="ms-auto" />
                      {c.stale && (
                        <button className="btn btn-sm btn-outline-warning" onClick={() => confirm(c.key)}>
                          Still valid
                        </button>
                      )}
                      <button className="icon-btn" title="Edit" onClick={() => setEditing({ item: c, pointKey: c.point_key })}>
                        <i className="bi bi-pencil" />
                      </button>
                      <button className="icon-btn text-danger" title="Delete" onClick={() => remove(c.key)}>
                        <i className="bi bi-trash" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))
          : (data.items as QuizQuestion[]).map((q) => (
              <div className="col-lg-6" key={q.key}>
                <div className="card h-100">
                  <div className="card-body d-flex flex-column gap-2">
                    <div className="d-flex align-items-center gap-2 small">
                      <span className="text-secondary text-truncate flex-grow-1">
                        <i className="bi bi-dot" />
                        {titles[q.point_key] ? <Bi as="span" en={titles[q.point_key].en} hu={titles[q.point_key].hu} /> : q.point_key}
                      </span>
                      {q.stale && <span className="badge-soft b-warning">outdated</span>}
                    </div>
                    <Bi en={q.question_en} hu={q.question_hu} md className="fw-semibold" />
                    {q.figure && <FigureView figure={q.figure} />}
                    <ol type="A" className="mb-0 small ps-3">
                      {q.options.map((o, i) => (
                        <li key={i} className={i === q.correct_index ? "text-success fw-semibold" : ""}>
                          <Bi as="span" en={o.en} hu={o.hu} />
                          {i === q.correct_index && <i className="bi bi-check-lg ms-1" />}
                        </li>
                      ))}
                    </ol>
                    {(q.why_en || q.why_hu) && (
                      <div className="small text-secondary border-top pt-2">
                        <Bi en={q.why_en} hu={q.why_hu} md />
                      </div>
                    )}
                    <div className="d-flex align-items-center gap-1 mt-auto">
                      <SrsLine srs={q.srs} />
                      <span className="ms-auto" />
                      {q.stale && (
                        <button className="btn btn-sm btn-outline-warning" onClick={() => confirm(q.key)}>
                          Still valid
                        </button>
                      )}
                      <button className="icon-btn" title="Edit" onClick={() => setEditing({ item: q, pointKey: q.point_key })}>
                        <i className="bi bi-pencil" />
                      </button>
                      <button className="icon-btn text-danger" title="Delete" onClick={() => remove(q.key)}>
                        <i className="bi bi-trash" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
      </div>
      {editing && <ItemEditor chapter={chapter} kind={kind} item={editing.item} pointKey={editing.pointKey} sha={data.sha} onHide={() => setEditing(null)} />}
      <RawEditorModal show={raw} onHide={() => setRaw(false)} slug={slug} chapterKey={chapter.key} kind={kind} />
    </>
  );
}
