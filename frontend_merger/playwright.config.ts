import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config — frontend_merger smoke.
 *
 * Assumption: dev server already running on :3003 (via `bun run dev` or dev-stack).
 * If not, enable `webServer` block below.
 */
export default defineConfig({
	testDir: "./tests",
	fullyParallel: false,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	workers: 1,
	reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
	use: {
		baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3003",
		headless: true,
		trace: "retain-on-failure",
		screenshot: "only-on-failure",
	},
	projects: [
		{
			name: "chromium",
			use: { ...devices["Desktop Chrome"] },
		},
	],
	// webServer: {
	// 	command: "bun run dev",
	// 	url: "http://127.0.0.1:3003",
	// 	reuseExistingServer: true,
	// 	timeout: 120_000,
	// },
});
