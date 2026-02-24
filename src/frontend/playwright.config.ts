import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { defineConfig } from '@playwright/test'

const frontendRoot = fileURLToPath(new URL('./', import.meta.url))
const repoRoot = path.resolve(frontendRoot, '..', '..')

const backendBaseUrl = 'http://127.0.0.1:8000'
const frontendBaseUrl = 'http://127.0.0.1:4173'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  use: {
    baseURL: frontendBaseUrl,
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: 'PYTHONPATH=src uv run uvicorn reportr.app.web_api:app --host 127.0.0.1 --port 8000',
      cwd: repoRoot,
      url: `${backendBaseUrl}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command:
        'VITE_API_BASE_URL=http://127.0.0.1:8000 bun run build-only && bun run preview --host 127.0.0.1 --port 4173 --strictPort',
      cwd: frontendRoot,
      url: frontendBaseUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
})
