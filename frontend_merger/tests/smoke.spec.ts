/**
 * Playwright Smoke Tests — frontend_merger
 *
 * Ziel: headless-Verify der 5 Routen + Agent-Sheet-Toggle ohne Backend-Stack.
 *
 * Run:
 *   cd frontend_merger
 *   bun run dev         # separates terminal, lauscht auf :3003
 *   bunx playwright test
 */

import { expect, test } from "@playwright/test";

const BASE = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3003";

test.use({ baseURL: BASE });

test("landing: Agent Testbed loads with 3 surface cards", async ({ page }) => {
	await page.goto("/");
	await expect(page).toHaveTitle(/Matrix · Frontend Merger/);
	await expect(page.getByRole("heading", { name: "Agent Testbed" })).toBeVisible();
	// Card titles use a heading-like <div>; locate by role instead of plain text
	// (plain "Matrix Chat" also appears in the intro paragraph).
	await expect(page.getByRole("link", { name: /Matrix Chat/ })).toBeVisible();
	await expect(page.getByRole("link", { name: /Control UI/ })).toBeVisible();
	// Agent Chat card is not a link (Sheet-toggle only)
	await expect(page.locator("text=Agent Chat").nth(0)).toBeVisible();
	await expect(page.locator("#tambo-canvas")).toBeVisible();
});

test("top bar: Matrix + Control links + Agent toggle render", async ({ page }) => {
	await page.goto("/");
	await expect(page.getByTestId("link-matrix")).toBeVisible();
	await expect(page.getByTestId("link-control")).toBeVisible();
	await expect(page.getByTestId("link-agent")).toBeVisible();
});

test("agent toggle: Sheet opens via Agent button + closes", async ({ page }) => {
	await page.goto("/");
	await page.waitForLoadState("networkidle");
	const agentBtn = page.getByTestId("link-agent");
	await expect(agentBtn).toBeVisible();
	await expect(agentBtn).toHaveAttribute("aria-pressed", "false");

	// Click and check the functional outcome (sheet dialog renders).
	// aria-pressed sometimes lags a render behind the state change in dev-mode;
	// the authoritative signal is the rendered [role="dialog"].
	await agentBtn.click({ force: true });
	const sheet = page.locator('[role="dialog"]');
	await expect(sheet.first()).toBeVisible({ timeout: 10_000 });

	// Toggle off (close button or click agent again)
	await agentBtn.click({ force: true });
	await expect(sheet.first()).toBeHidden({ timeout: 10_000 });
});

test("/matrix: shows config hint without credentials", async ({ page }) => {
	await page.goto("/matrix");
	// Ohne MATRIX_* env vars rendert die Page einen Konfigurationshinweis.
	await expect(page.getByRole("heading", { name: "Matrix nicht konfiguriert" })).toBeVisible();
});

test("/control/skills: renders without crash", async ({ page }) => {
	const resp = await page.goto("/control/skills");
	expect(resp?.status(), "HTTP status").toBe(200);
	// TopBar persistiert
	await expect(page.getByTestId("link-control")).toBeVisible();
});

test("/memory: renders without crash", async ({ page }) => {
	const resp = await page.goto("/memory");
	expect(resp?.status(), "HTTP status").toBe(200);
	await expect(page.getByTestId("link-matrix")).toBeVisible();
});

test("/files: renders without crash", async ({ page }) => {
	const resp = await page.goto("/files");
	expect(resp?.status(), "HTTP status").toBe(200);
	await expect(page.getByTestId("link-matrix")).toBeVisible();
});

test("tambo canvas placeholder visible on landing", async ({ page }) => {
	await page.goto("/");
	const canvas = page.locator("#tambo-canvas");
	await expect(canvas).toBeVisible();
	await expect(canvas).toHaveAttribute("aria-label", "Generative UI canvas");
});
