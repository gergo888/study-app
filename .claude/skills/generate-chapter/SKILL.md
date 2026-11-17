---
name: generate-chapter
description: Generate or refresh the bilingual (EN+HU) summary, flashcards and quiz of one chapter of a study material in this app, as Markdown files. Use when asked to generate content for a chapter (e.g. "/generate-chapter comptia-a-plus 1B"), or with --refresh to update flashcards/quiz after the summary was edited.
argument-hint: "[--refresh] <material-slug> <chapter-key>"
---

# Generate chapter content

This app has no AI integration of its own: **you** write the learning content as Markdown files
that the app reads. Read `docs/CONTENT_FORMAT.md` before writing anything — the parser is strict.

Run commands from `backend/` with `.venv/bin/python manage.py …`.

## New chapter

1. **Prepare the source.** `prepare_chapter <slug> <key>` writes
   `content/<slug>/<key>/_source/text.md` (text with `<!-- page N -->` markers and the section list)
   and candidate figures in `_source/figures/` + `_source/figures.json`
   (key, page, caption, size).
2. **Read everything.** Read the whole `text.md`. Look at every candidate figure image whose
   caption suggests it carries information (diagrams, connectors, tables); skip decorative photos.
   If an important diagram is vector art and has no candidate, render it with
   `crop_figure <slug> <key> <page> x0,y0,x1,y1`.
3. **Write `summary.md`.**
   * Sections follow the chapter's own sections (skip the "Review Activity" section — its questions
     are good inspiration for quiz questions though).
   * Each bullet point is one learnable fact or idea, with a short, specific **bold title** (this
     is what stays visible in memorize mode, so the title must be a cue, not the answer) and a
     body of 1–4 sentences. Prefer exact numbers, names, standards, and comparisons — this is
     exam material. Aim for roughly 4–8 points per section, 15–40 per chapter.
   * Write both `en` and `hu`. Hungarian should read naturally (not word-for-word) and keep the
     established English IT terms where Hungarian practice does (USB, HDMI, port, SATA…), adding a
     Hungarian explanation where helpful.
   * `concepts`: 2–5 key concepts per point, each with its English and Hungarian wording, common
     abbreviations and unit spellings (`5 m | 5 méter | 5 meters`). They are matched fuzzily against
     what the learner types.
   * Attach a figure only where seeing it really helps (connector shapes, port layouts, diagrams).
     Reference candidates as `figures/<file name>`; `check_content` copies them from `_source/`.
4. **Write `flashcards.md`**: at least one card per point (`## <point-id>`). The front asks one
   precise question; the back answers it briefly. Add a second card (`## <id> (2)`) when a point
   has two independent facts worth testing.
5. **Write `quiz.md`**: at least one question per point. Four options, exactly one correct, three
   plausible distractors from the same domain (no "all of the above", no joke answers). Vary the
   position of the correct answer. Always add `why-en`/`why-hu` explaining why the answer is right
   (and why a tempting distractor is wrong).
6. **Validate.** `check_content <slug> <key>` must print `OK`. Fix every error and warning it reports
   and run it again until it does.

## Refresh (`--refresh`)

The learner edited bullet points in the app; their flashcards/quiz questions are now "stale".

1. `stale_report <slug> <key>` lists stale cards, points without cards, and orphans.
2. Read the current `summary.md`, `flashcards.md`, `quiz.md`.
3. Rewrite **only** the listed entries so they match the current point text; add missing ones,
   remove orphans. Keep every id unchanged — the review history hangs on them. Do not touch
   `summary.md` unless asked.
4. `check_content <slug> <key>` until `OK`.

## Rules

* Never rename or reuse ids of existing points/cards unless the user asks.
* Never edit `data/*.csv` by hand; `check_content` / `reindex_content` keep them in sync.
* Only the files in `content/<slug>/<key>/` (and `figures/`) are yours to write.
