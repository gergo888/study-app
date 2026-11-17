# StudyDesk — notes for Claude Code

Single-user study app: `backend/` (Django + DRF, no database) and `frontend/` (Next.js 16).
Learning content is Markdown in `content/`, state is CSV in `data/`, PDFs are in `media/`.
Start with `docs/ARCHITECTURE.md`.

## Generating learning content

Use the `generate-chapter` skill (`/generate-chapter <slug> <key>`, `--refresh` after summary edits).
The Markdown syntax is strict — `docs/CONTENT_FORMAT.md`. Always finish with
`backend/.venv/bin/python manage.py check_content <slug> <key>` printing `OK`.
Never rename existing `{#ids}`: progress and spaced-repetition history are attached to them.

## Rules

- Never edit `data/*.csv` by hand; they are maintained by the app and `reindex_content`.
- Backend: run Python through `backend/.venv/bin/python`; tests with `.venv/bin/python -m pytest` from `backend/`.
  Storage roots come from settings (`CONTENT_ROOT`, `DATA_ROOT`, `MEDIA_ROOT`); tests use temp folders.
- All writes to content or CSV go through `apps/core/csvstore.data_lock()` and atomic writes
  (`csvstore.Table.update`, `content/repository.write_text`).
- Django URLs end with `/`; the frontend always calls `/api/...` paths with a trailing slash.
- Frontend: this Next.js version differs from older ones — read `frontend/node_modules/next/dist/docs/`
  before using an API you are unsure about. Pages are client components rendered behind the browser-only
  boundary in `src/app/providers.tsx`; `proxy.ts` is the former middleware.
- Check frontend changes with `npm run lint` and `npm run build` in `frontend/`.
