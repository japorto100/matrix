"use client";

// Control Page — Phase 22b
// Shell: top nav + subtab routing. URL is source of truth (AC4, AC.V3).

import { usePathname } from "next/navigation";
import { ControlTopNav } from "./components/ControlTopNav";
import { ControlAgentsTab } from "./components/subtabs/ControlAgentsTab";
import { ControlEvalsTab } from "./components/subtabs/ControlEvalsTab";
import { ControlKGContextTab } from "./components/subtabs/ControlKGContextTab";
import { ControlMemoryTab } from "./components/subtabs/ControlMemoryTab";
import { ControlOverviewTab } from "./components/subtabs/ControlOverviewTab";
import { ControlSecurityTab } from "./components/subtabs/ControlSecurityTab";
import { ControlSessionsTab } from "./components/subtabs/ControlSessionsTab";
import { ControlSkillsTab } from "./components/subtabs/ControlSkillsTab";
import { ControlToolEventsTab } from "./components/subtabs/ControlToolEventsTab";

export function ControlPage() {
	const pathname = usePathname();

	const renderTab = () => {
		if (pathname === "/control" || pathname === "/control/overview") {
			return <ControlOverviewTab />;
		}
		if (pathname === "/control/sessions") {
			return <ControlSessionsTab />;
		}
		if (pathname === "/control/security") {
			return <ControlSecurityTab />;
		}
		if (pathname === "/control/tool-events") {
			return <ControlToolEventsTab />;
		}
		if (pathname === "/control/memory") {
			return <ControlMemoryTab />;
		}
		if (pathname === "/control/kg-context") {
			return <ControlKGContextTab />;
		}
		if (pathname === "/control/skills") {
			return <ControlSkillsTab />;
		}
		if (pathname === "/control/agents") {
			return <ControlAgentsTab />;
		}
		if (pathname === "/control/evals") {
			return <ControlEvalsTab />;
		}
		return <ControlOverviewTab />;
	};

	return (
		<div className="flex h-full flex-col bg-background">
			<ControlTopNav />
			<div className="flex flex-1 flex-col overflow-y-auto">{renderTab()}</div>
		</div>
	);
}
