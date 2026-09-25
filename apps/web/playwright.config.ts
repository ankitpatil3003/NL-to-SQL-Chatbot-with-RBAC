import { defineConfig, devices } from "@playwright/test";

// End-to-end tests against a running stack (docker compose up, or the deployed URL):
//   npx playwright test                      # fast UI tests (no LLM calls)
//   E2E_LIVE=1 npx playwright test           # + one real question through the whole stack
//   E2E_BASE_URL=https://... npx playwright test
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false, // tests share demo users and one-turn-per-user limits
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
