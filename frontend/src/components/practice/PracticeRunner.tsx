"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Bi, FigureView } from "@/components/common/ui";
import { api } from "@/lib/api";
import { usePrefs } from "@/lib/prefs";
import { useToast } from "@/lib/toast";
import type { ActivityResult, AnswerResult, CheckResult, PracticeItem } from "@/lib/types";

type Outcome = { key: string; correct: boolean; xp: number };

function useKeys(handler: (e: KeyboardEvent) => void) {
  useEffect(() => {
    const fn = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t.tagName === "TEXTAREA" || t.tagName === "INPUT") return;
      handler(e);
    };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, [handler]);
}

/** Compact context line (one language only, so it stays on one line). */
function ItemHeader({ item }: { item: PracticeItem }) {
  const { primary } = usePrefs();
  const hu = primary === "hu";
  return (
    <div className="small text-secondary mb-2 text-truncate">
      <span className="fw-semibold text-primary">{item.chapter}</span> · {hu ? item.section_hu || item.section_en : item.section_en} ·{" "}
      {hu ? item.point_title_hu || item.point_title_en : item.point_title_en}
    </div>
  );
}

const RATINGS = [
  { value: 1, label: "Again", hint: "forgot", cls: "btn-outline-danger" },
  { value: 2, label: "Hard", hint: "barely", cls: "btn-outline-warning" },
  { value: 3, label: "Good", hint: "recalled", cls: "btn-outline-success" },
  { value: 4, label: "Easy", hint: "instantly", cls: "btn-outline-primary" },
];

function FlashcardStep({ item, onAnswer }: { item: Extract<PracticeItem, { kind: "flashcard" }>; onAnswer: (rating: number) => void }) {
  const [flipped, setFlipped] = useState(false);
  const c = item.data;
  const keys = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        setFlipped(true);
      } else if (flipped && ["1", "2", "3", "4"].includes(e.key)) onAnswer(Number(e.key));
    },
    [flipped, onAnswer],
  );
  useKeys(keys);
  return (
    <>
      <div className="card flashcard mb-3" onClick={() => setFlipped(true)}>
        <div className="card-body">
          <ItemHeader item={item} />
          <div className="side-label">Question</div>
          <Bi en={c.front_en} hu={c.front_hu} md />
          {c.figure && <FigureView figure={c.figure} className="" />}
          {flipped ? (
            <div className="border-top mt-4 pt-3">
              <div className="side-label">Answer</div>
              <Bi en={c.back_en} hu={c.back_hu} md />
            </div>
          ) : (
            <div className="text-secondary small mt-4">
              Click or press <kbd>Space</kbd> to show the answer
            </div>
          )}
        </div>
      </div>
      {flipped && (
        <div className="rating-btns">
          {RATINGS.map((r) => (
            <button key={r.value} className={`btn ${r.cls}`} onClick={() => onAnswer(r.value)}>
              {r.label}
              <small>
                {r.hint} · {r.value}
              </small>
            </button>
          ))}
        </div>
      )}
    </>
  );
}

function QuizStep({
  item,
  onAnswer,
  onNext,
}: {
  item: Extract<PracticeItem, { kind: "quiz" }>;
  onAnswer: (selected: number) => Promise<AnswerResult | null>;
  onNext: () => void;
}) {
  const q = item.data;
  const [order] = useState(() => [0, 1, 2, 3].sort(() => Math.random() - 0.5));
  const [picked, setPicked] = useState<number | null>(null);
  const [correctIndex, setCorrectIndex] = useState<number | null>(null);
  const pick = useCallback(
    async (original: number) => {
      if (picked !== null) return;
      setPicked(original);
      const res = await onAnswer(original);
      setCorrectIndex(res?.correct_index ?? q.correct_index);
    },
    [picked, onAnswer, q.correct_index],
  );
  const keys = useCallback(
    (e: KeyboardEvent) => {
      if (picked === null && ["1", "2", "3", "4"].includes(e.key)) void pick(order[Number(e.key) - 1]);
      else if (picked !== null && correctIndex !== null && e.key === "Enter") onNext();
    },
    [picked, correctIndex, order, pick, onNext],
  );
  useKeys(keys);
  return (
    <>
      <div className="card mb-3">
        <div className="card-body">
          <ItemHeader item={item} />
          <Bi en={q.question_en} hu={q.question_hu} md className="fs-5 fw-semibold mb-2" />
          {q.figure && <FigureView figure={q.figure} className="quiz-figure mb-2" />}
        </div>
      </div>
      {order.map((original, pos) => {
        const o = q.options[original];
        let cls = "";
        if (correctIndex !== null) {
          if (original === correctIndex) cls = "correct";
          else if (original === picked) cls = "wrong";
        }
        return (
          <button key={original} className={`quiz-option ${cls}`} disabled={picked !== null} onClick={() => pick(original)}>
            <span className="letter">{"ABCD"[pos]}</span>
            <Bi as="span" en={o.en} hu={o.hu} />
          </button>
        );
      })}
      {correctIndex !== null && (
        <div className="card mt-2">
          <div className="card-body">
            <div className={`fw-semibold mb-1 ${picked === correctIndex ? "text-success" : "text-danger"}`}>
              <i className={`bi ${picked === correctIndex ? "bi-check-circle" : "bi-x-circle"} me-1`} />
              {picked === correctIndex ? "Correct!" : "Not quite."}
            </div>
            {(q.why_en || q.why_hu) && <Bi en={q.why_en} hu={q.why_hu} md className="small" />}
            <div className="text-end mt-2">
              <button className="btn btn-primary" onClick={onNext} autoFocus>
                Next <kbd className="ms-1">Enter</kbd>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function WriteStep({ item, onDone }: { item: Extract<PracticeItem, { kind: "write" }>; onDone: (result: ActivityResult) => void }) {
  const { primary } = usePrefs();
  const [text, setText] = useState("");
  const [check, setCheck] = useState<CheckResult | null>(null);
  const p = item.data;
  const run = async () => {
    setCheck(await api<CheckResult>(`/chapters/${item.material}/${item.chapter}/points/${p.key}/check-answer/`, { body: { text, lang: primary } }));
  };
  return (
    <div className="card">
      <div className="card-body">
        <ItemHeader item={item} />
        <Bi en={p.title_en} hu={p.title_hu} className="fs-5 fw-semibold mb-3" />
        <textarea className="form-control mb-2" rows={4} value={text} onChange={(e) => setText(e.target.value)} disabled={!!check} autoFocus placeholder={primary === "hu" ? "Írd le, amire emlékszel…" : "Write down what you remember…"} />
        {!check ? (
          <div className="d-flex gap-2">
            <button className="btn btn-primary" onClick={run} disabled={!text.trim()}>
              Check
            </button>
            <button className="btn btn-light" onClick={() => setCheck({ score: 0, verdict: "wrong", matched: [], missed: p.concepts, original: "" })}>
              I don&apos;t know
            </button>
          </div>
        ) : (
          <>
            <div className="mb-2">
              {check.matched.map((g, i) => (
                <span key={`m${i}`} className="concept-tag b-success">
                  <i className="bi bi-check me-1" />
                  {g[0]}
                </span>
              ))}
              {check.missed.map((g, i) => (
                <span key={`x${i}`} className="concept-tag b-danger">
                  <i className="bi bi-x me-1" />
                  {g[0]}
                </span>
              ))}
            </div>
            <div className="point-body border rounded p-2 mb-2">
              <Bi en={p.body_en} hu={p.body_hu} md />
              {p.figure && <FigureView figure={p.figure} />}
            </div>
            <div className="small fw-semibold mb-1">
              Suggested: {check.verdict} ({Math.round(check.score * 100)}%) — your verdict:
            </div>
            <div className="d-flex gap-2">
              <button className={`btn btn-sm ${check.verdict === "correct" ? "btn-success" : "btn-outline-success"}`} onClick={() => onDone("correct")}>
                Correct
              </button>
              <button className={`btn btn-sm ${check.verdict === "partial" ? "btn-warning" : "btn-outline-warning"}`} onClick={() => onDone("partial")}>
                Partly
              </button>
              <button className={`btn btn-sm ${check.verdict === "wrong" ? "btn-danger" : "btn-outline-danger"}`} onClick={() => onDone("wrong")}>
                Wrong
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export function PracticeRunner({ items, context, backHref, title }: { items: PracticeItem[]; context: "learn" | "review"; backHref: string; title: string }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [index, setIndex] = useState(0);
  const [outcomes, setOutcomes] = useState<Outcome[]>([]);

  const item = items[index];
  const finished = index >= items.length;
  const next = useCallback(() => setIndex((i) => i + 1), []);

  const afterAnswer = (res: { chapter_learned?: string | null; xp_awarded?: number }) => {
    if (res.xp_awarded) {
      toast(`+${res.xp_awarded} XP`, "xp");
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    }
    if (res.chapter_learned) toast(`Chapter learned (via ${res.chapter_learned})! 🎉`, "success");
  };

  const answerCard = async (body: Record<string, unknown>): Promise<AnswerResult | null> => {
    try {
      const res = await api<AnswerResult>("/practice/answer/", { body: { material: item.material, chapter: item.chapter, kind: item.kind, card_key: item.key, context, ...body } });
      setOutcomes((o) => [...o, { key: item.key, correct: res.correct, xp: res.xp_awarded }]);
      afterAnswer(res);
      return res;
    } catch (e) {
      toast(e instanceof Error ? e.message : "Could not save the answer", "error");
      return null;
    }
  };

  useEffect(() => {
    if (finished && outcomes.length) {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
      qc.invalidateQueries({ queryKey: ["chapter"] });
      qc.invalidateQueries({ queryKey: ["cards"] });
      qc.invalidateQueries({ queryKey: ["material"] });
    }
  }, [finished, outcomes.length, qc]);

  if (!items.length) {
    return (
      <div className="card">
        <div className="empty-state">
          <i className="bi bi-inbox" />
          Nothing to practise here.
          <div className="mt-3">
            <Link href={backHref} className="btn btn-sm btn-primary">
              Back
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (finished) {
    const correct = outcomes.filter((o) => o.correct).length;
    const xp = outcomes.reduce((s, o) => s + o.xp, 0);
    return (
      <div className="practice-wrap">
        <div className="card text-center">
          <div className="card-body py-5">
            <i className="bi bi-trophy text-warning" style={{ fontSize: "3rem" }} />
            <h2 className="h4 mt-2">Session complete</h2>
            <p className="text-secondary">
              {items.length} items · {correct} correct · <span className="fw-semibold text-warning">+{xp} XP</span>
            </p>
            <div className="d-flex gap-2 justify-content-center">
              <Link href={backHref} className="btn btn-primary">
                Done
              </Link>
              <button
                className="btn btn-outline-primary"
                onClick={() => {
                  setIndex(0);
                  setOutcomes([]);
                }}
              >
                Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="practice-wrap">
      <div className="d-flex align-items-center gap-3 mb-3">
        <Link href={backHref} className="icon-btn" title="Exit">
          <i className="bi bi-x-lg" />
        </Link>
        <div className="flex-grow-1">
          <div className="d-flex justify-content-between small mb-1">
            <span className="fw-semibold">{title}</span>
            <span className="text-secondary">
              {index + 1} / {items.length}
            </span>
          </div>
          <div className="progress" style={{ height: 6 }}>
            <div className="progress-bar" style={{ width: `${(index / items.length) * 100}%` }} />
          </div>
        </div>
      </div>
      {item.kind === "flashcard" && (
        <FlashcardStep
          key={item.material + item.chapter + item.key}
          item={item}
          onAnswer={async (rating) => {
            await answerCard({ rating });
            next();
          }}
        />
      )}
      {item.kind === "quiz" && (
        <QuizStep key={item.material + item.chapter + item.key} item={item} onAnswer={(selected) => answerCard({ selected_index: selected })} onNext={next} />
      )}
      {item.kind === "write" && (
        <WriteStep
          key={item.material + item.chapter + item.key}
          item={item}
          onDone={async (result) => {
            try {
              const res = await api<{ chapter_learned: string | null }>(`/chapters/${item.material}/${item.chapter}/points/${item.key}/activity/`, {
                body: { kind: "write", result, context },
              });
              setOutcomes((o) => [...o, { key: item.key, correct: result === "correct", xp: 0 }]);
              afterAnswer(res);
            } catch {
              toast("Could not save progress", "error");
            }
            next();
          }}
        />
      )}
    </div>
  );
}
