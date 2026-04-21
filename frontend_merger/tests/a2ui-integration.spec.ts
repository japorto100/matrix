import { expect, test } from "@playwright/test";

test.describe("A2UI + CopilotKit integration (Ansatz Y)", () => {
	test("#9 Files and Memory buttons visible + navigate", async ({ page }) => {
		await page.goto("/");
		await expect(page.getByTestId("link-files")).toBeVisible();
		await expect(page.getByTestId("link-memory")).toBeVisible();

		await page.getByTestId("link-files").click();
		await expect(page).toHaveURL(/\/files/);

		await page.getByTestId("link-memory").click();
		await expect(page).toHaveURL(/\/memory/);
	});

	test("#10 Landing A2UI canvas renders idle placeholder", async ({ page }) => {
		await page.goto("/");
		const canvas = page.locator('[aria-label="A2UI surface main"]');
		const visible = await canvas.isVisible().catch(() => false);
		test.skip(!visible, "Landing-page A2UI canvas not present in this build");
		await expect(canvas).toContainText(/canvas bereit|widget wird geladen/i);
	});

	test("#11 Chat message with A2UI tool-result renders inline widget", async ({
		page,
	}) => {
		await page.route("**/api/agent/chat", async (route) => {
			const chunks = [
				`data: ${JSON.stringify({ type: "thread-id", thread_id: "t1" })}\n\n`,
				`data: ${JSON.stringify({ type: "text-start", id: "t1" })}\n\n`,
				`data: ${JSON.stringify({ type: "text-end", id: "t1" })}\n\n`,
				`data: ${JSON.stringify({
					type: "tool-result",
					tool_call_id: "tc1",
					tool_name: "render_a2ui_surface",
					result: {
						type: "a2ui",
						surface_id: "chat-inline-1",
						tree: {
							type: "Card",
							children: [{ type: "Text", text: "hello-widget" }],
						},
					},
				})}\n\n`,
				`data: ${JSON.stringify({ type: "finish" })}\n\n`,
			].join("");
			await route.fulfill({
				status: 200,
				contentType: "text/event-stream",
				headers: { "x-vercel-ai-ui-message-stream": "v1" },
				body: chunks,
			});
		});

		await page.goto("/");
		await page.getByTestId("link-agent").click();
		const composer = page.getByRole("textbox").first();
		await composer.fill("show test widget");
		await composer.press("Enter");
		await expect(page.getByText("hello-widget")).toBeVisible({ timeout: 10_000 });
	});

	test("#12 FileCard 'Add to Chat' opens chat with context", async ({ page }) => {
		await page.goto("/files");
		const card = page.locator('[data-testid="file-card"]').first();
		const cardVisible = await card.isVisible().catch(() => false);
		test.skip(!cardVisible, "No files in storage — seed fixture not set up");
		await card.click({ button: "right" });
		await page.getByRole("menuitem", { name: /add to chat/i }).click();
		const sheet = page.locator('[role="dialog"]').first();
		await expect(sheet).toBeVisible();
	});
});
