import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
	title: "Control",
	description: "Agent runtime control surface: sessions, memory, security, tools, agents.",
};

export default function ControlLayout({ children }: { children: ReactNode }) {
	return <div className="h-screen overflow-hidden">{children}</div>;
}
