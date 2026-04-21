import { NextResponse } from "next/server";

// Stub: full implementation pending go-appservice route.
// CopilotKit action calls this from FilesPageCopilot — returns 501 so the
// action reports a graceful error to the LLM instead of crashing the UI.
export async function POST() {
	return NextResponse.json(
		{
			error: "save-attachment not yet implemented — go-appservice route pending",
		},
		{ status: 501 },
	);
}
