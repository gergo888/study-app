# StudyDesk — frontend

Next.js (App Router, TypeScript) user interface of the study app. It talks to the Django API under
`/api/*` (proxied to `BACKEND_URL`, default `http://127.0.0.1:8000`, by `next.config.ts`).

```bash
npm install
npm run dev      # http://localhost:3000 (Django must run on :8000)
npm run lint
npm run build && npm start
```

See [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) for what every folder and file does.
