"use client";

// ControlPage — Control surface entry point (Slice 7 Two-Tier)
// User Mode default routes: /control (Overview), /agents, /permissions, /skills,
//                            /tools, /sessions, /security
// Developer Mode routes: + /system, /api, /sandbox, /audit, /mcp, /a2a
// URL is source of truth via usePathname; Mode via useControlMode (URL param + localStorage, D20).

import { usePathname } from "next/navigation";
import { ControlPageCopilot } from "./ControlPageCopilot";
import { A2aTab } from "./components/A2aTab";
import { AgentsTab } from "./components/AgentsTab";
import { ApiModelsTab } from "./components/ApiModelsTab";
import { AuditTab } from "./components/AuditTab";
import { ContextTab } from "./components/ContextTab";
import { ControlTopNav } from "./components/ControlTopNav";
import { McpTab } from "./components/McpTab";
import { OpsRoomTab } from "./components/OpsRoomTab";
import { OverviewTab } from "./components/OverviewTab";
import { PermissionsTab } from "./components/PermissionsTab";
import { ReportsTab } from "./components/ReportsTab";
import { SandboxTab } from "./components/SandboxTab";
import { SecurityTab } from "./components/SecurityTab";
import { SemanticTab } from "./components/SemanticTab";
import { SessionsTab } from "./components/SessionsTab";
import { SkillsTab } from "./components/SkillsTab";
import { SystemTab } from "./components/SystemTab";
import { TasksTab } from "./components/TasksTab";
import { ToolsTab } from "./components/ToolsTab";

export function ControlPage() {
	const pathname = usePathname();

	const renderSubtab = () => {
		// ─── User Mode Tabs ─────────────────────────────────────────────────
		if (pathname.startsWith("/control/agents")) return <AgentsTab />;
		if (pathname.startsWith("/control/permissions")) return <PermissionsTab />;
		if (pathname.startsWith("/control/skills")) return <SkillsTab />;
		if (pathname.startsWith("/control/tools")) return <ToolsTab />;
		if (pathname.startsWith("/control/sessions")) return <SessionsTab />;
		if (pathname.startsWith("/control/tasks")) return <TasksTab />;
		if (pathname.startsWith("/control/context")) return <ContextTab />;
		if (pathname.startsWith("/control/semantic")) return <SemanticTab />;
		if (pathname.startsWith("/control/reports")) return <ReportsTab />;
		if (pathname.startsWith("/control/security")) return <SecurityTab />;

		// ─── Developer Mode Tabs ────────────────────────────────────────────
		// Legacy /control/system/env path is redirected to /control/api (ApiModelsTab)
		if (pathname.startsWith("/control/api") || pathname.startsWith("/control/system/env")) {
			return <ApiModelsTab />;
		}
		if (pathname.startsWith("/control/system")) return <SystemTab />;
		if (pathname.startsWith("/control/sandbox")) return <SandboxTab />;
		if (pathname.startsWith("/control/audit")) return <AuditTab />;
		if (pathname.startsWith("/control/ops")) return <OpsRoomTab />;
		if (pathname.startsWith("/control/mcp")) return <McpTab />;
		if (pathname.startsWith("/control/a2a")) return <A2aTab />;

		// Default /control or /control/overview → Overview
		return <OverviewTab />;
	};

	return (
		<div className="flex flex-col h-full">
			<ControlPageCopilot />
			<ControlTopNav />
			<div className="flex-1 overflow-auto">{renderSubtab()}</div>
		</div>
	);
}
