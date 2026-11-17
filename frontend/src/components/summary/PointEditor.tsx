"use client";

import { useState } from "react";
import Modal from "react-bootstrap/Modal";

import { ErrorAlert, IssueList, Loader } from "@/components/common/ui";
import {
  BiField,
  FigureField,
  type FigureRef,
  figurePayload,
  figureRef,
  type FlashcardForm,
  FlashcardFields,
  flashcardForm,
  type QuizForm,
  QuizFields,
  quizForm,
} from "@/components/editor/fields";
import { api, issuesOf } from "@/lib/api";
import { useFlashcards, useInvalidateChapter, useQuiz } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import type { Point } from "@/lib/types";

interface PointForm {
  title_en: string;
  title_hu: string;
  body_en: string;
  body_hu: string;
  concepts: string;
  figure: FigureRef;
}

const conceptsText = (c: string[][]) => c.map((g) => g.join(" | ")).join(" ; ");

const pointForm = (p: Point | null): PointForm =>
  p
    ? { title_en: p.title_en, title_hu: p.title_hu, body_en: p.body_en, body_hu: p.body_hu, concepts: conceptsText(p.concepts), figure: figureRef(p.figure) }
    : { title_en: "", title_hu: "", body_en: "", body_hu: "", concepts: "", figure: null };

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

interface EditorProps {
  onHide: () => void;
  slug: string;
  chapterKey: string;
  point: Point | null; // null = new point
  sectionKey: string;
  summarySha: string | null;
}

/** Edits one bullet point together with its linked flashcard and quiz question. Mount it to open it. */
export function PointEditor(props: EditorProps) {
  const flashcards = useFlashcards(props.slug, props.chapterKey);
  const quiz = useQuiz(props.slug, props.chapterKey);
  if (flashcards.isLoading || quiz.isLoading) {
    return (
      <Modal show onHide={props.onHide} centered>
        <Modal.Body>
          <Loader />
        </Modal.Body>
      </Modal>
    );
  }
  return <PointEditorForm {...props} />;
}

function PointEditorForm({ onHide, slug, chapterKey, point, sectionKey, summarySha }: EditorProps) {
  const flashcards = useFlashcards(slug, chapterKey);
  const quiz = useQuiz(slug, chapterKey);
  const invalidate = useInvalidateChapter();
  const toast = useToast();

  const linkedCard = point ? flashcards.data?.items.find((c) => c.point_key === point.key) : undefined;
  const linkedQuestion = point ? quiz.data?.items.find((q) => q.point_key === point.key) : undefined;

  const [form, setForm] = useState<PointForm>(pointForm(point));
  const [card, setCard] = useState<FlashcardForm>(flashcardForm(linkedCard, point?.key ?? ""));
  const [question, setQuestion] = useState<QuizForm>(quizForm(linkedQuestion, point?.key ?? ""));
  const [withCard, setWithCard] = useState(!!linkedCard);
  const [withQuestion, setWithQuestion] = useState(!!linkedQuestion);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const textChanged = point && (form.title_en !== point.title_en || form.title_hu !== point.title_hu || form.body_en !== point.body_en || form.body_hu !== point.body_hu);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = { ...form, figure: figurePayload(form.figure) };
      const res = await api<{ sha: string; key?: string }>(`/chapters/${slug}/${chapterKey}/summary/`, {
        body: point
          ? { op: "update_point", point_key: point.key, point: payload, base_sha: summarySha }
          : { op: "add_point", section_key: sectionKey, point: payload, base_sha: summarySha },
      });
      const pointKey = point?.key ?? res.key!;
      const cardChanged = withCard && !same(card, flashcardForm(linkedCard, pointKey));
      if (cardChanged) {
        await api(`/chapters/${slug}/${chapterKey}/flashcards/`, {
          body: { op: "upsert", base_sha: flashcards.data?.sha ?? null, item: { ...card, point_key: pointKey, figure: figurePayload(card.figure) } },
        });
      }
      const questionChanged = withQuestion && !same(question, quizForm(linkedQuestion, pointKey));
      if (questionChanged) {
        await api(`/chapters/${slug}/${chapterKey}/quiz/`, {
          body: { op: "upsert", base_sha: quiz.data?.sha ?? null, item: { ...question, point_key: pointKey, figure: figurePayload(question.figure) } },
        });
      }
      invalidate(slug, chapterKey);
      toast(point ? "Point saved" : "Point added", "success");
      onHide();
    } catch (err) {
      setError(err);
      invalidate(slug, chapterKey);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal show onHide={onHide} size="xl" centered backdrop="static" scrollable>
      <form onSubmit={save} className="d-contents">
        <Modal.Header closeButton>
          <Modal.Title className="h5">{point ? "Edit bullet point" : "New bullet point"}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <ErrorAlert error={error} />
          <IssueList issues={issuesOf(error)} />
          <BiField label="Bullet point (visible in memorize mode)" en={form.title_en} hu={form.title_hu} onChange={(en, hu) => setForm({ ...form, title_en: en, title_hu: hu })} required />
          <BiField label="Text (hidden in memorize mode — Markdown allowed)" rows={4} en={form.body_en} hu={form.body_hu} onChange={(en, hu) => setForm({ ...form, body_en: en, body_hu: hu })} required />
          <div className="mb-3">
            <label className="form-label small fw-semibold mb-1">Key concepts (used to check written answers)</label>
            <input className="form-control form-control-sm" value={form.concepts} onChange={(e) => setForm({ ...form, concepts: e.target.value })} placeholder="480 Mbps | 480 Mb/s ; 5 m | 5 méter ; Hi-Speed" />
            <div className="form-text">Separate concepts with <code>;</code> and alternative wordings (EN/HU) with <code>|</code>.</div>
          </div>
          <FigureField slug={slug} chapterKey={chapterKey} value={form.figure} onChange={(figure) => setForm({ ...form, figure })} />

          {textChanged && (linkedCard || linkedQuestion) && (
            <div className="alert alert-warning small py-2">
              <i className="bi bi-exclamation-triangle me-1" />
              You changed the text. Update the linked flashcard and quiz question below — otherwise they are marked <strong>outdated</strong> until you confirm them or Claude Code refreshes them.
            </div>
          )}

          <hr />
          <div className="d-flex align-items-center gap-2 mb-2">
            <h3 className="h6 mb-0">
              <i className="bi bi-card-text me-1" />
              Linked flashcard
            </h3>
            {!linkedCard && (
              <div className="form-check form-switch ms-2 mb-0">
                <input className="form-check-input" type="checkbox" id="with-card" checked={withCard} onChange={(e) => setWithCard(e.target.checked)} />
                <label className="form-check-label small" htmlFor="with-card">
                  add one
                </label>
              </div>
            )}
          </div>
          {withCard && <FlashcardFields slug={slug} chapterKey={chapterKey} value={card} onChange={setCard} />}

          <hr />
          <div className="d-flex align-items-center gap-2 mb-2">
            <h3 className="h6 mb-0">
              <i className="bi bi-patch-question me-1" />
              Linked quiz question
            </h3>
            {!linkedQuestion && (
              <div className="form-check form-switch ms-2 mb-0">
                <input className="form-check-input" type="checkbox" id="with-q" checked={withQuestion} onChange={(e) => setWithQuestion(e.target.checked)} />
                <label className="form-check-label small" htmlFor="with-q">
                  add one
                </label>
              </div>
            )}
          </div>
          {withQuestion && <QuizFields slug={slug} chapterKey={chapterKey} value={question} onChange={setQuestion} />}
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-light" onClick={onHide}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={busy}>
            {busy && <span className="spinner-border spinner-border-sm me-1" />}
            Save
          </button>
        </Modal.Footer>
      </form>
    </Modal>
  );
}
