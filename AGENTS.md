- Keep changes simple and minimal.
- Run commands from the repo root.
- Do not run dev servers unless explicitly asked.
- Do not run Docker commands unless explicitly asked.

## Stack
- Backend: Python 3.13+ with FastAPI (`fastapi[standard]`)
- Frontend: Vue 3 + Vite + TypeScript
- Styling: Tailwind CSS + PostCSS
- Package managers: `uv` (Python), `bun` (frontend)

## Backend Rules
- Use `uv` for Python commands and dependency management (no direct `pip install`).
- Avoid `Any` unless unavoidable.
- Do not add helper code only to satisfy type checks.
- Prefer `X | Y` over `Union[X, Y]` when possible.

## Frontend Rules
- Use `.vue` SFCs with `<script setup lang="ts">`.
- Props and emits must be explicitly typed.
- Prefer `shadcn-vue` for interactive primitives (inputs, dialogs, toasts, form controls).
- Use Tailwind utilities for layout/page styling.
- Keep HTTP calls in a service/composable layer.
- Use `fetch` or a lightweight wrapper (no Axios unless explicitly approved).
- Keep frontend types aligned with backend schemas.

## Validation
- If Python files changed: `uv run ruff format . && uv run basedpyright && uv run pytest`
- If frontend files changed: `bun run lint && bun run build` (`bun run test` if available)

## Safety
- Never commit secrets (`.env`, keys, tokens).
