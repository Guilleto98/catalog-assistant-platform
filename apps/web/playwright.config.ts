import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e',
  timeout: 600000,
  workers: 1,
  retries: 0,
  use: {
    baseURL: 'http://localhost:4200',
    viewport: { width: 1440, height: 960 },
    screenshot: 'off',
    trace: 'off',
    video: 'off',
  }, // No traces with login credentials.
  reporter: [['list']],
});
