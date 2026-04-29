import { describe, expect, it } from "vitest";
import type { MatrixWidgetApprovalItem } from "../types";
import { filterWidgetProposals } from "./WidgetApprovalsTab";

const proposals: MatrixWidgetApprovalItem[] = [
	{
		proposal_id: "report-widget-risk-brief",
		report_id: "risk-brief",
		title: "Risk Brief",
		room_id: "!risk:example.test",
		requester_user_id: "@agent:example.test",
		url: "https://widgets.example/reports/risk-brief",
		status: "pending",
		approval_required: true,
		can_approve: true,
		can_deny: true,
		denial_reasons: [],
		fallback_markdown: "[Risk Brief](https://widgets.example/reports/risk-brief)",
		permissions: ["read_room"],
		audit_refs: ["audit-report-build"],
		report_artifact: {
			manifest_id: "risk-brief/manifest.json",
			output_path: "risk-brief/report.html",
			renderer: "markdown-fallback",
		},
	},
	{
		proposal_id: "report-widget-blocked",
		title: "Blocked Widget",
		room_id: "!risk:example.test",
		requester_user_id: "@agent:example.test",
		status: "blocked",
		approval_required: false,
		can_approve: false,
		can_deny: false,
		denial_reasons: ["widget-origin-not-allowed"],
		fallback_markdown: "Blocked Widget (blocked widget URL)",
		permissions: [],
		audit_refs: [],
	},
];

describe("filterWidgetProposals", () => {
	it("filters by status and report artifact metadata", () => {
		const filtered = filterWidgetProposals(proposals, "manifest", "pending");

		expect(filtered).toHaveLength(1);
		expect(filtered[0]?.proposal_id).toBe("report-widget-risk-brief");
	});

	it("matches policy denial reasons", () => {
		const filtered = filterWidgetProposals(proposals, "origin-not-allowed", "all");

		expect(filtered).toHaveLength(1);
		expect(filtered[0]?.status).toBe("blocked");
	});
});
