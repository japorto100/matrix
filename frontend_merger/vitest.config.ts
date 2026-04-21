import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
	plugins: [react()],
	resolve: {
		alias: {
			"@": resolve(__dirname, "./src"),
			"@matrix": resolve(__dirname, "./src/features/matrix"),
			"@agent": resolve(__dirname, "./src/features/agent"),
			"@control": resolve(__dirname, "./src/features/control"),
		},
	},
	test: {
		environment: "happy-dom",
		globals: false,
		include: ["src/**/*.{test,spec}.{ts,tsx}"],
		exclude: ["node_modules", "tests"],
	},
});
