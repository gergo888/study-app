"use client";

import { useState } from "react";

import { Bi, FigureView } from "@/components/common/ui";
import { api } from "@/lib/api";
import { usePrefs } from "@/lib/prefs";
import { useToast } from "@/lib/toast";
import type { ActivityResult, CheckResult, Point } from "@/lib/types";

type Stage = "hidden" | "menu" | "words" | "write" | "revealed";

/** Markdown -> plain words for the word-by-word reveal. */
export function plainWords(text: string): string[] {
  return text
    .replace(/\*\*|__|`/g, "")
    .replace(/^\s*[-*]\s+/gm, "• ")
    .split(/\s+/)
    .filter(Boolean);
}

const VERDICT: Record<CheckResult["verdict"], { label: string; cls: string }> = {
  correct: { label: "Looks correct", cls: "b-success" },
  partial: { label: "Partly correct", cls: "b-warning" },
  wrong: { label: "Missing key concepts", cls: "b-danger" },
};

export function MemorizeBody({
  slug,
  chapterKey,
  point,
  onRecorded,
  resetToken,
}: {
  slug: string;
  chapterKey: string;
  point: Point;
  onRecorded: (learned: string | null) => void;
  resetToken: number;
}) {
  const { primary } = usePrefs();
  const toast = useToast();
  const [stage, setStage] = useState<Stage>("hidden");
  const [shown, setShown] = useState(0);
  const [answer, setAnswer] = useState("");
  const [check, setCheck] = useState<CheckResult | null>(null);
  const [lastReset, setLastReset] = useState(resetToken);
  if (resetToken !== lastReset) {
    setLastReset(resetToken);
    setStage("hidden");
    setShown(0);
    setAnswer("");
    setCheck(null);
  }

  const body = primary === "hu" ? point.body_hu : point.body_en;
  const words = plainWords(body);

  const record = async (kind: "reveal" | "write", result: ActivityResult) => {
    try {
      const res = await api<{ chapter_learned: string | null }>(`/chapters/${slug}/${chapterKey}/points/${point.key}/activity/`, {
        body: { kind, result, context: "learn" },
      });
      onRecorded(res.chapter_learned);
    } catch {
      toast("Could not save progress", "error");
    }
  };

  const revealAll = () => {
    setStage("revealed");
    void record("reveal", "seen");
  };
  const nextWord = () => {
    const n = shown + 1;
    setShown(n);
    if (n >= words.length) revealAll();
  };
  const runCheck = async () => {
    const res = await api<CheckResult>(`/chapters/${slug}/${chapterKey}/points/${point.key}/check-answer/`, { body: { text: answer, lang: primary } });
    setCheck(res);
  };
  const confirm = (result: ActivityResult) => {
    setStage("revealed");
    setCheck(null);
    void record("write", result);
  };

  if (stage === "revealed") {
    return (
      <div className="point-body">
        <Bi en={point.body_en} hu={point.body_hu} md />
        {point.figure && <FigureView figure={point.figure} />}
        <button className="btn btn-link btn-sm p-0 mt-1 text-secondary" onClick={() => { setStage("hidden"); setShown(0); setAnswer(""); }}>
          <i className="bi bi-eye-slash me-1" />
          Hide again
        </button>
      </div>
    );
  }

  if (stage === "words") {
    return (
      <div>
        <div className="point-body word-reveal" onClick={nextWord} role="button" tabIndex={0} onKeyDown={(e) => (e.key === " " || e.key === "Enter") && (e.preventDefault(), nextWord())} title="Click or press Space for the next word">
          {words.map((w, i) =>
            i < shown ? (
              <span key={i}>{w} </span>
            ) : (
              <span key={i}>
                <span className="w-hidden" style={{ width: `${Math.max(1.2, w.length * 0.55)}em` }} />{" "}
              </span>
            ),
          )}
        </div>
        {/* key: remount so focus moves to "Next word" instead of staying on the reused menu button */}
        <div className="reveal-menu" key="words-menu">
          <button className="btn btn-sm btn-soft" onClick={nextWord} autoFocus>
            Next word <kbd className="ms-1">Space</kbd>
          </button>
          <button className="btn btn-sm btn-light" onClick={revealAll}>
            Reveal all
          </button>
        </div>
      </div>
    );
  }

  if (stage === "write") {
    return (
      <div className="mt-2">
        <textarea
          className="form-control"
          rows={3}
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder={primary === "hu" ? "Írd le saját szavaiddal…" : "Write it down in your own words…"}
          autoFocus
          disabled={!!check}
        />
        {!check ? (
          <div className="reveal-menu">
            <button className="btn btn-sm btn-primary" onClick={runCheck} disabled={!answer.trim()}>
              <i className="bi bi-check2-square me-1" />
              Check
            </button>
            <button className="btn btn-sm btn-light" onClick={() => setStage("hidden")}>
              Cancel
            </button>
          </div>
        ) : (
          <div className="card mt-2">
            <div className="card-body py-2">
              <div className="d-flex align-items-center gap-2 mb-2">
                <span className={`badge-soft ${VERDICT[check.verdict].cls}`}>{VERDICT[check.verdict].label}</span>
                <span className="small text-secondary">{Math.round(check.score * 100)}% of key concepts</span>
              </div>
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
              <div className="small text-secondary mb-1">Original:</div>
              <div className="point-body small">
                <Bi en={point.body_en} hu={point.body_hu} md />
              </div>
              <div className="small fw-semibold mt-2 mb-1">Your verdict (you can override the suggestion):</div>
              <div className="d-flex gap-2 flex-wrap">
                <button className={`btn btn-sm ${check.verdict === "correct" ? "btn-success" : "btn-outline-success"}`} onClick={() => confirm("correct")}>
                  Correct
                </button>
                <button className={`btn btn-sm ${check.verdict === "partial" ? "btn-warning" : "btn-outline-warning"}`} onClick={() => confirm("partial")}>
                  Partly
                </button>
                <button className={`btn btn-sm ${check.verdict === "wrong" ? "btn-danger" : "btn-outline-danger"}`} onClick={() => confirm("wrong")}>
                  Wrong
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  const bars = Math.min(4, Math.max(1, Math.ceil(body.length / 110)));
  return (
    <div>
      <div className="hidden-body" onClick={() => setStage(stage === "menu" ? "hidden" : "menu")} role="button" aria-label="Hidden text — click to reveal">
        {Array.from({ length: bars }).map((_, i) => (
          <div key={i} className="bar" style={{ width: i === bars - 1 && bars > 1 ? "60%" : "100%" }} />
        ))}
      </div>
      {stage === "menu" && (
        <div className="reveal-menu" key="reveal-menu">
          <button className="btn btn-sm btn-soft" onClick={revealAll}>
            <i className="bi bi-eye me-1" />
            Reveal all
          </button>
          <button className="btn btn-sm btn-soft" onClick={() => setStage("words")}>
            <i className="bi bi-fonts me-1" />
            Word by word
          </button>
          <button className="btn btn-sm btn-soft" onClick={() => setStage("write")}>
            <i className="bi bi-pencil me-1" />
            Write it
          </button>
        </div>
      )}
    </div>
  );
}
