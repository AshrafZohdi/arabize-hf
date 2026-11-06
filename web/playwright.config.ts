import { defineConfig, devices } from '@playwright/test'

// Smoke test of the demo path. By default it starts the production build in DEMO_MODE (recorded Fanar answers, no
// endpoint), so it is deterministic. BASE_URL=https://fayezalkh12-darby.hf.space runs it against the live Space.
const base = process.env.BASE_URL ?? 'http://127.0.0.1:7870'

export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  fullyParallel: false,
  reporter: 'list',
  use: { baseURL: base, trace: 'retain-on-failure' },
  projects: [
    { name: 'phone-360', use: { ...devices['Pixel 7'], viewport: { width: 360, height: 780 } } },
    { name: 'desktop-1280', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 900 } } },
  ],
  webServer: process.env.BASE_URL
    ? undefined
    : {
        command: 'cd .. && DEMO_MODE=1 DARBY_TERMBANK=off MCP_ENABLED=0 .venv/bin/uvicorn server.main:app --port 7870',
        url: 'http://127.0.0.1:7870/api/health',
        reuseExistingServer: false,
        timeout: 60_000,
      },
})
