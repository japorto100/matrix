import { Suspense } from "react";
import { AgentChatPanel } from "@/AgentChatPanel";

export default function AgentChatPage() {
	return (
		<main className="h-dvh w-full">
			<Suspense>
				<AgentChatPanel />
			</Suspense>
		</main>
	);
}
