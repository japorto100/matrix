import { describe, expect, it } from "vitest";

import { extractSkillsGuardVerdict } from "./SkillsGuardDrawer";

describe("extractSkillsGuardVerdict", () => {
	it("extracts dangerous multi-rejection payloads from the root body", () => {
		const verdict = extractSkillsGuardVerdict(
			{
				success: false,
				suggested_action: "hitl_confirm",
				rejected: [
					{
						name: "danger-skill",
						verdict: "dangerous",
						trust_level: "community",
						reason: "blocked",
						findings: [{ pattern_id: "x", severity: "critical" }],
					},
				],
			},
			"https://github.com/example/skills",
		);

		expect(verdict?.source).toBe("danger-skill");
		expect(verdict?.verdict).toBe("dangerous");
		expect(verdict?.trustLevel).toBe("community");
		expect(verdict?.reason).toBe("blocked");
		expect(verdict?.findings).toHaveLength(1);
	});

	it("unwraps FastAPI HTTPException detail bodies from the BFF proxy", () => {
		const verdict = extractSkillsGuardVerdict(
			{
				detail: {
					success: false,
					suggested_action: "hitl_confirm",
					rejected: [
						{
							name: "wrapped-skill",
							verdict: "dangerous",
							findings: [],
						},
					],
				},
			},
			"fallback-source",
		);

		expect(verdict?.source).toBe("wrapped-skill");
		expect(verdict?.verdict).toBe("dangerous");
	});

	it("extracts single archive-install payloads", () => {
		const verdict = extractSkillsGuardVerdict(
			{
				suggested_action: "hitl_confirm",
				skill_name: "archive-skill",
				verdict: "dangerous",
				message: "needs review",
				findings: [],
			},
			"fallback-source",
		);

		expect(verdict?.source).toBe("archive-skill");
		expect(verdict?.reason).toBe("needs review");
	});

	it("ignores non-HITL bodies", () => {
		expect(extractSkillsGuardVerdict({ detail: "bad request" }, "src")).toBeNull();
		expect(extractSkillsGuardVerdict({ success: false }, "src")).toBeNull();
	});
});
