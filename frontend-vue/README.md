# frontend-vue (Vue 3 SPA)

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
- **`VITE_ENABLE_MSW`**: Set to `true` to mock HTTP with MSW in **dev only** (`src/main.ts` starts the worker). Vitest continues to use the Node MSW server from `src/test/setup.ts`.

## Layout

- `src/api/` — Axios wrappers and DTO types
- `src/stores/` — Pinia (`auth`, `chat`)
- `src/views/` — Route-level pages
- `src/components/` — UI building blocks
- `src/mocks/` — MSW handlers shared by tests (and optional browser dev)

## Testing

- Unit/integration: **Vitest** + **Testing Library** + **MSW** (`src/test/setup.ts`).
- E2E: **Playwright**; see repo doc [../docs/E2E.md](../docs/E2E.md).
