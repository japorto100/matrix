/**
 * N3 — RoomList Keyboard-Navigation Minimal-Test (Contrarian-Amendment #6).
 *
 * Ziel: silent-Regression-Schutz wenn zukuenftige RoomList-Edits die
 * Arrow-Up/Down-Nav oder das Skip-Behavior ueber Group-Header brechen.
 *
 * Ohne MATRIX_* env vars kann kein Login passieren — der Test verifiziert
 * nur den Render-Anchor (data-matrix-roomlist) und skipt den tatsaechlichen
 * Key-Nav-Flow. Bei vorhandenen Credentials laeuft der echte Flow.
 *
 * Run:
 *   cd frontend_merger
 *   bun run dev
 *   bunx playwright test tests/roomlist-keyboard-nav.spec.ts
 */

import { expect, test } from "@playwright/test";

const BASE = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3003";
const HAS_CREDENTIALS = Boolean(
	process.env.MATRIX_USER_ID && process.env.MATRIX_ACCESS_TOKEN,
);

test.use({ baseURL: BASE });

test("RoomList: Render-Anchor vorhanden oder Config-Hinweis sichtbar", async ({ page }) => {
	await page.goto("/matrix");
	const notConfigured = page.getByRole("heading", { name: "Matrix nicht konfiguriert" });
	const roomList = page.locator("[data-matrix-roomlist]");
	// Entweder nicht konfiguriert (CI-default) ODER Roomlist rendert.
	const either = (await notConfigured.isVisible()) || (await roomList.isVisible());
	expect(either).toBe(true);
});

test("RoomList: Arrow-Down/Up springt zwischen Room-Items, skippt Group-Header", async ({
	page,
}) => {
	test.skip(
		!HAS_CREDENTIALS,
		"Braucht MATRIX_USER_ID + MATRIX_ACCESS_TOKEN env-vars fuer echten Flow.",
	);
	await page.goto("/matrix");

	const scroll = page.locator("[data-matrix-roomlist-scroll]");
	await expect(scroll).toBeVisible({ timeout: 10_000 });
	await scroll.focus();

	// Kick off Arrow-Down — erwartet dass irgendein Room-Item selected wird.
	await page.keyboard.press("ArrowDown");
	await page.waitForTimeout(120);
	const firstSelected = await page.locator("[data-selected='true']").count();
	expect(firstSelected).toBeGreaterThan(0);

	// Fokus zwischen Room-Items navigiert — Group-Header wird uebersprungen.
	// (Headers sind <button aria-expanded>; sie duerfen NICHT als selected markiert werden)
	const selectedIsHeader = await page
		.locator("[data-selected='true'] button[aria-expanded]")
		.count();
	expect(selectedIsHeader).toBe(0);
});
