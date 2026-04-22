import { A2uiCanvas } from "@agent/components/A2uiCanvas";
import { Bot, MessageSquare, SlidersHorizontal, Sparkles } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Landing / Agent Testbed.
 *
 * Der Merger-Shell ist bewusst minimal gehalten. Dieser Bereich dient als
 * Buehne fuer Generative-UI-Experimente via A2UI v0.9 (Google-standard):
 *
 *   - A2UI-Widgets (python-agent streamed Widget-Messages → @a2ui/web/core v0.9
 *     renderer → components aus features/agent/components/a2ui/registry.ts).
 *   - CopilotKit AG-UI Actions koennen Frontend-State mutieren (z.B. Karten
 *     einblenden, Layouts umschalten) — via BFF /api/copilotkit → python-agent.
 *   - Agent-Sheet wird ueber den Agent-Button in der TopBar geoeffnet und
 *     emittiert UI-Fragmente gegen diesen Slot.
 */
export default function LandingPage() {
	return (
		<div className="h-full overflow-auto">
			<div className="mx-auto max-w-5xl space-y-6 p-8">
				<header className="space-y-2">
					<div className="flex items-center gap-2">
						<Sparkles className="h-5 w-5 text-primary" />
						<h1 className="text-3xl font-bold tracking-tight">Agent Testbed</h1>
					</div>
					<p className="text-muted-foreground">
						Test-Harness, der Matrix Chat, Agent Chat und Control UI unter einer Shell mountet.
						Diese Seite ist absichtlich leer — hier rendern A2UI- und CopilotKit-Komponenten, die
						der Agent generiert. Agent-Sheet oeffnen via{" "}
						<kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-xs">
							Agent
						</kbd>{" "}
						in der Top-Bar.
					</p>
				</header>

				{/* Main Canvas — standalone dashboard, surfaceId="main" */}
				<A2uiCanvas surfaceId="main" />

				<section className="grid gap-4 md:grid-cols-3">
					<Link href="/matrix" className="group">
						<Card className="h-full transition-colors hover:border-primary/50">
							<CardHeader>
								<div className="flex items-center gap-2">
									<MessageSquare className="h-5 w-5 text-primary" />
									<CardTitle className="text-lg">Matrix Chat</CardTitle>
								</div>
								<CardDescription>
									Mensch↔Mensch Messenger auf Basis matrix-js-sdk 41. Eigene Route
									&#40;Fullscreen&#41;.
								</CardDescription>
							</CardHeader>
							<CardContent>
								<ul className="space-y-1 font-mono text-xs text-muted-foreground">
									<li>· matrix-js-sdk</li>
									<li>· LiveKit Calls</li>
									<li>· Rust-Crypto WASM</li>
								</ul>
							</CardContent>
						</Card>
					</Link>

					<Card className="h-full border-emerald-500/30">
						<CardHeader>
							<div className="flex items-center gap-2">
								<Bot className="h-5 w-5 text-emerald-500" />
								<CardTitle className="text-lg">Agent Chat</CardTitle>
							</div>
							<CardDescription>
								Sheet-Overlay statt Route. Agent-Button in der TopBar togglet das Panel —
								funktioniert auf jeder Seite.
							</CardDescription>
						</CardHeader>
						<CardContent>
							<ul className="space-y-1 font-mono text-xs text-muted-foreground">
								<li>· ai v6 / AI SDK</li>
								<li>· A2UI v0.9 + CopilotKit</li>
								<li>· use-mcp / WebMCP</li>
							</ul>
						</CardContent>
					</Card>

					<Link href="/control" className="group">
						<Card className="h-full transition-colors hover:border-primary/50">
							<CardHeader>
								<div className="flex items-center gap-2">
									<SlidersHorizontal className="h-5 w-5 text-primary" />
									<CardTitle className="text-lg">Control UI</CardTitle>
								</div>
								<CardDescription>
									Admin-Konsole fuer Memory, Files, Knowledge Graph. Eigene Route
									&#40;Fullscreen&#41;.
								</CardDescription>
							</CardHeader>
							<CardContent>
								<ul className="space-y-1 font-mono text-xs text-muted-foreground">
									<li>· XYFlow KG-Graph</li>
									<li>· Recharts</li>
									<li>· TanStack Query</li>
								</ul>
							</CardContent>
						</Card>
					</Link>
				</section>

				<section className="space-y-2 rounded-lg border border-border bg-card p-4">
					<h2 className="text-sm font-semibold">Status</h2>
					<ul className="space-y-1 text-xs text-muted-foreground">
						<li>
							<span className="font-mono">Port:</span> 3003 (dev) — isolierte Apps bleiben auf
							3000/3001/3002
						</li>
						<li>
							<span className="font-mono">Scope:</span> CopilotKit + A2UI v0.9 (Google-Standard)
							Generative-UI + Shared Shell ohne Hauptprojekt-Abhaengigkeit
						</li>
						<li>
							<span className="font-mono">Branch:</span>{" "}
							<code>claude/merge-frontend-chat-ui-2OqmH</code>
						</li>
					</ul>
				</section>
			</div>
		</div>
	);
}
