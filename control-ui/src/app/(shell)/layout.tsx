import type { ReactNode } from "react";
import { GlobalTopBar } from "@/components/GlobalTopBar";

export default function ShellLayout({ children }: { children: ReactNode }) {
	return (
		<div className="flex min-h-screen flex-col">
			<GlobalTopBar />
			<main className="flex-1 overflow-auto">{children}</main>
		</div>
	);
}
