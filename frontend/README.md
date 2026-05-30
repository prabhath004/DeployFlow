# deployflow — frontend

A lightweight, Vercel-inspired web UI for the DeployFlow FastAPI backend.

## Stack

- Vite 5 + React 18 + TypeScript (strict)
- Tailwind CSS 3
- react-router-dom 6
- No state library — just React state + a single `useAuth` context.

## Run

```sh
cd frontend
npm install
npm run dev
# open http://localhost:5173
```

The dev server is pinned to port `5173` because the backend's CORS allowlist
includes that origin.

Build a production bundle:

```sh
npm run build      # type-checks + builds into dist/
npm run preview    # serves the built dist/
```

## Environment

By default the UI talks to `http://localhost:8000`. To point at a different
backend, set `VITE_API_BASE` before `dev` / `build`:

```sh
VITE_API_BASE=https://api.example.com npm run dev
```

A starter `.env.example` is included — copy to `.env.local` and edit.

## Pages

| Route               | Purpose                                                                                 |
| ------------------- | --------------------------------------------------------------------------------------- |
| `/login`            | Sign-in / register tabbed card. Stores JWT in `localStorage["deployflow_token"]`.       |
| `/projects`         | Grid of projects. Inline "New project" form (name + repo URL + branch).                 |
| `/projects/:id`     | Project header + deployments list. Per-row Retry / Cancel. "Deploy" button top-right.   |
| `/deployments/:id`  | Full deployment detail, polled status badge, and a live SSE log viewer.                 |

## Auth

- The JWT is read from `localStorage["deployflow_token"]` on every API call.
- `apiFetch()` attaches `Authorization: Bearer …` automatically.
- A 401 from any endpoint clears the token and redirects to `/login`.

## Live logs (SSE)

The backend's `/deployments/{id}/logs/stream` requires `Authorization: Bearer …`.
The browser's native `EventSource` cannot set custom headers, so the viewer
uses `fetch()` + a tiny SSE parser (see `src/api/client.ts → openSse`). The
public shape mirrors `EventSource` (`onOpen` / `onEvent` / `onError` /
`onClose`), and the handle is closed cleanly on unmount.

The viewer:

- Loads historical logs first, then attaches the live stream.
- Auto-scrolls to the bottom unless the user has scrolled up.
- Polls `/status` every 1s and stops once the deployment reaches a terminal
  state (`SUCCEEDED`, `FAILED`, `CANCELLED`).

## File layout

```
src/
  api/
    client.ts       # apiFetch + openSse + ApiError + token handling
    types.ts        # Project / Deployment / LogEntry / User / Status
  auth/
    AuthContext.tsx # { user, token, login, register, logout, loading }
  components/
    Button.tsx
    Card.tsx
    Header.tsx      # Logo, Header, Shell
    Input.tsx
    Skeleton.tsx    # Skeleton, EmptyState, ErrorMessage
    StatusBadge.tsx
  lib/
    time.ts         # relativeTime, formatTimestamp, logTimestamp
  pages/
    LoginPage.tsx
    ProjectsPage.tsx
    ProjectDetailPage.tsx
    DeploymentDetailPage.tsx
  App.tsx
  main.tsx
  index.css
  vite-env.d.ts
```

## Notes

- Dark theme only. The mono logo (`▲ deployflow`) is the brand mark.
- Status colors: gray for queued/pending/retrying, amber (with a pulsing dot)
  for in-flight states, green for succeeded, red for failed, slate for
  cancelled.
- No toast/modal libraries; inline `<ErrorMessage>` is used everywhere.
