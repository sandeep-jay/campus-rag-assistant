# Vue chat UI

The primary **Campus RAG Assistant** interface—conversations, streaming answers, sources, and feedback.

Setup and overview: root [README](../README.md).

## Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Vite dev server (proxies `/api` to backend when configured) |
| `npm run build` | Production build |
| `npm run test` | Vitest |
| `npm run e2e` | Playwright (requires API — see [../docs/E2E.md](../docs/E2E.md)) |
| `npm run lint` | ESLint |

## Environment

Copy [`.env.example`](./.env.example) to `.env.local` as needed.

- **`VITE_API_URL`**: Backend origin (e.g. `http://localhost:8000`). Empty string uses same-origin + Vite proxy.
- **`VITE_ENABLE_MSW`**: Set to `true` to mock HTTP with MSW in **dev only** (`src/main.ts` starts the worker). Vitest uses the Node MSW server from `src/test/setup.ts`.

## Layout

| Path | Role |
|------|------|
| `src/views/ChatView.vue` | Main chat page |
| `src/components/chat/` | Messages, sources, feedback, input |
| `src/components/sidebar/` | Session list and navigation |
| `src/stores/chat.ts` | Sessions, streaming send, fallback to `/api/chat/chat` |
| `src/utils/normalizeAssistantContent.ts` | Light markdown cleanup before render |
| `src/api/` | Axios wrappers and DTO types |
| `src/mocks/` | MSW handlers for tests and optional dev mocking |

## Testing

- Unit/integration: **Vitest** + **Testing Library** + **MSW** (`src/test/setup.ts`).
- E2E: **Playwright** — [../docs/E2E.md](../docs/E2E.md).
