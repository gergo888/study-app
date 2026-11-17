# StudyDesk

A personal learning-support app. Import a textbook PDF, study it chapter by chapter, and practise with
bilingual (English + Hungarian) summaries, flashcards and quizzes, with spaced repetition and XP.
Claude Code writes the learning content; the app stores everything as Markdown and CSV files — no
database.

* **Frontend:** `frontend/` — Next.js (React, TypeScript, Bootstrap)
* **Backend:** `backend/` — Django + Django REST Framework
* **Content:** `content/` (Markdown) · **State:** `data/` (CSV) · **PDFs:** `media/`

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for what every folder and file does.
For a tour of everything the app can do, see [docs/FEATURES.md](docs/FEATURES.md)
(magyarul: [docs/FEATURES.hu.md](docs/FEATURES.hu.md)).

## Run it locally

Requirements: Python 3.12, Node.js 20+.

```bash
# Backend (terminal 1)
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env                       # then set SECRET_KEY to a long random string
.venv/bin/python manage.py set_password    # choose your login password
.venv/bin/python manage.py import_pdf comptia-a-plus ~/Downloads/comptia.pdf   # once
.venv/bin/python manage.py runserver 127.0.0.1:8000

# Frontend (terminal 2)
cd frontend
npm install
npm run dev                                # open http://localhost:3000
```

## Generate content for a chapter

Content is written by Claude Code using the project skill in `.claude/skills/generate-chapter/`.
In Claude Code, inside this repository:

```
/generate-chapter comptia-a-plus 1B            # new chapter
/generate-chapter --refresh comptia-a-plus 1A  # update flashcards/quiz after editing the summary
```

The skill runs `prepare_chapter`, writes `content/<slug>/<key>/{summary,flashcards,quiz}.md` and
validates them with `check_content`. The app shows the new content immediately. The format is
described in [docs/CONTENT_FORMAT.md](docs/CONTENT_FORMAT.md).

## Useful backend commands

| Command | What it does |
|---|---|
| `manage.py set_password` | Set / change the login password (logs out all browsers). |
| `manage.py import_pdf <slug> <file.pdf> [--level N]` | Create a material from a PDF and build its chapters. |
| `manage.py prepare_chapter <slug> <key>` | Extract a chapter's text and figures for Claude Code. |
| `manage.py check_content <slug> <key>` | Validate a chapter's Markdown and reindex it. |
| `manage.py stale_report <slug> <key>` | List flashcards/quiz questions outdated by summary edits. |
| `manage.py reindex_content --all` | Rebuild the CSV index from all Markdown files. |

## Tests

```bash
cd backend && .venv/bin/python -m pytest
cd frontend && npm run lint && npm run build
```

## Backups

Everything personal is in `content/`, `data/`, `media/` and `backend/.env`. Copy those folders to back up
or move the app (e.g. to a VPS — see the deployment outline in docs/ARCHITECTURE.md).
