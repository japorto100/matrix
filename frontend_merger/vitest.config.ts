import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
	plugins: [react()],
	test: {
		environment: "happy-dom",
		globals: false,
		include: ["src/**/*.{test,spec}.{ts,tsx}"],
		exclude: ["node_modules", "tests"],
	},
});
