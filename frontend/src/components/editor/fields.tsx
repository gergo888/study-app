"use client";

import { useState } from "react";

import type { Figure, Flashcard, QuizQuestion } from "@/lib/types";

import { FigurePicker } from "./FigurePicker";

export type FigureRef = { path: string; caption_en: string; caption_hu: string; url?: string } | null;

export interface FlashcardForm {
  key?: string;
  point_key: string;
  front_en: string;
  front_hu: string;
  back_en: string;
  back_hu: string;
  figure: FigureRef;
}

export interface QuizForm {
  key?: string;
  point_key: string;
  question_en: string;
  question_hu: string;
  options: { en: string; hu: string }[];
  correct_index: number;
  why_en: string;
  why_hu: string;
  figure: FigureRef;
}

export const figureRef = (f: Figure | null): FigureRef => (f ? { path: f.path, caption_en: f.caption_en, caption_hu: f.caption_hu, url: f.url } : null);

export const flashcardForm = (c: Flashcard | undefined, pointKey: string): FlashcardForm =>
  c
    ? { key: c.key, point_key: c.point_key, front_en: c.front_en, front_hu: c.front_hu, back_en: c.back_en, back_hu: c.back_hu, figure: figureRef(c.figure) }
    : { point_key: pointKey, front_en: "", front_hu: "", back_en: "", back_hu: "", figure: null };

export const quizForm = (q: QuizQuestion | undefined, pointKey: string): QuizForm =>
  q
    ? {
        key: q.key,
        point_key: q.point_key,
        question_en: q.question_en,
        question_hu: q.question_hu,
        options: q.options.map((o) => ({ ...o })),
        correct_index: q.correct_index,
        why_en: q.why_en,
        why_hu: q.why_hu,
        figure: figureRef(q.figure),
      }
    : {
        point_key: pointKey,
        question_en: "",
        question_hu: "",
        options: [0, 1, 2, 3].map(() => ({ en: "", hu: "" })),
        correct_index: 0,
        why_en: "",
        why_hu: "",
        figure: null,
      };

/** Two inputs side by side: English and Hungarian. */
export function BiField({
  label,
  en,
  hu,
  onChange,
  rows = 1,
  required = false,
}: {
  label: string;
  en: string;
  hu: string;
  onChange: (en: string, hu: string) => void;
  rows?: number;
  required?: boolean;
}) {
  const Input = rows > 1 ? "textarea" : "input";
  return (
    <div className="mb-3">
      <label className="form-label small fw-semibold mb-1">{label}</label>
      <div className="row g-2">
        <div className="col-md-6">
          <div className="input-group input-group-sm">
            <span className="input-group-text">EN</span>
            <Input className="form-control" rows={rows} value={en} required={required} onChange={(e) => onChange(e.target.value, hu)} />
          </div>
        </div>
        <div className="col-md-6">
          <div className="input-group input-group-sm">
            <span className="input-group-text">HU</span>
            <Input className="form-control" rows={rows} value={hu} onChange={(e) => onChange(en, e.target.value)} />
          </div>
        </div>
      </div>
    </div>
  );
}

export function FigureField({ slug, chapterKey, value, onChange }: { slug: string; chapterKey: string; value: FigureRef; onChange: (f: FigureRef) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-3">
      <label className="form-label small fw-semibold mb-1">Figure (only if it helps understanding)</label>
      {value ? (
        <div className="d-flex gap-3 align-items-start">
          {value.url && (
            // eslint-disable-next-line @next/next/no-img-element -- authenticated API image
            <img src={value.url} alt="" style={{ width: 120, height: 80, objectFit: "contain", background: "#fff", borderRadius: 6 }} />
          )}
          <div className="flex-grow-1">
            <BiField label="Caption" en={value.caption_en} hu={value.caption_hu} onChange={(en, hu) => onChange({ ...value, caption_en: en, caption_hu: hu })} />
          </div>
          <div className="d-flex flex-column gap-1">
            <button type="button" className="btn btn-sm btn-soft" onClick={() => setOpen(true)}>
              Change
            </button>
            <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => onChange(null)}>
              Remove
            </button>
          </div>
        </div>
      ) : (
        <div>
          <button type="button" className="btn btn-sm btn-soft" onClick={() => setOpen(true)}>
            <i className="bi bi-image me-1" />
            Choose figure
          </button>
        </div>
      )}
      <FigurePicker
        show={open}
        slug={slug}
        chapterKey={chapterKey}
        onHide={() => setOpen(false)}
        onPick={(f) => {
          onChange({ path: f.path, url: f.url, caption_en: value?.caption_en || f.caption, caption_hu: value?.caption_hu || f.caption });
          setOpen(false);
        }}
      />
    </div>
  );
}

export function FlashcardFields({ slug, chapterKey, value, onChange }: { slug: string; chapterKey: string; value: FlashcardForm; onChange: (v: FlashcardForm) => void }) {
  return (
    <>
      <BiField label="Front (question)" rows={2} en={value.front_en} hu={value.front_hu} onChange={(en, hu) => onChange({ ...value, front_en: en, front_hu: hu })} required />
      <BiField label="Back (answer)" rows={2} en={value.back_en} hu={value.back_hu} onChange={(en, hu) => onChange({ ...value, back_en: en, back_hu: hu })} required />
      <FigureField slug={slug} chapterKey={chapterKey} value={value.figure} onChange={(figure) => onChange({ ...value, figure })} />
    </>
  );
}

export function QuizFields({ slug, chapterKey, value, onChange }: { slug: string; chapterKey: string; value: QuizForm; onChange: (v: QuizForm) => void }) {
  const setOption = (i: number, en: string, hu: string) => {
    const options = value.options.map((o, n) => (n === i ? { en, hu } : o));
    onChange({ ...value, options });
  };
  return (
    <>
      <BiField label="Question" rows={2} en={value.question_en} hu={value.question_hu} onChange={(en, hu) => onChange({ ...value, question_en: en, question_hu: hu })} required />
      <label className="form-label small fw-semibold mb-1">Options — mark exactly one as correct</label>
      {value.options.map((o, i) => (
        <div className="d-flex gap-2 align-items-center mb-2" key={i}>
          <input
            className="form-check-input mt-0"
            type="radio"
            name={`correct-${value.key ?? "new"}`}
            checked={value.correct_index === i}
            onChange={() => onChange({ ...value, correct_index: i })}
            aria-label={`Option ${i + 1} is correct`}
          />
          <div className="input-group input-group-sm">
            <span className="input-group-text">{"ABCD"[i]}</span>
            <input className="form-control" placeholder="English" value={o.en} onChange={(e) => setOption(i, e.target.value, o.hu)} required />
            <input className="form-control" placeholder="Magyar (empty = same)" value={o.hu === o.en ? "" : o.hu} onChange={(e) => setOption(i, o.en, e.target.value)} />
          </div>
        </div>
      ))}
      <BiField label="Explanation" rows={2} en={value.why_en} hu={value.why_hu} onChange={(en, hu) => onChange({ ...value, why_en: en, why_hu: hu })} />
      <FigureField slug={slug} chapterKey={chapterKey} value={value.figure} onChange={(figure) => onChange({ ...value, figure })} />
    </>
  );
}

export const figurePayload = (f: FigureRef) => (f ? { path: f.path, caption_en: f.caption_en, caption_hu: f.caption_hu } : null);
