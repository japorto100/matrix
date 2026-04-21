// Control Surface — Slice 5 (Agent Config) + Slice 6 (System Observability)
// Routes /control, /control/{permissions, skills, sandbox, tools,
//                              system, system/env, audit, sessions, mcp, a2a}
// URL is source of truth; routing handled in ControlPage via usePathname.

import { ControlPage } from "@/features/control/ControlPage";

export default function ControlSubtabPage() {
	return <ControlPage />;
}
