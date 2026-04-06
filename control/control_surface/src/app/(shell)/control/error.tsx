"use client";

import { motion } from "framer-motion";
import { Activity, RefreshCcw, SlidersHorizontal } from "lucide-react";
import { useEffect, useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function ControlError({
	error,
	reset,
}: {
	error: Error & { digest?: string };
	reset: () => void;
}) {
	const [isPending, startTransition] = useTransition();

	useEffect(() => {
		console.error("CONTROL_SURFACE_FAULT", {
			severity: "HIGH",
			domain: "Control",
			subdomain: "AgentRuntime",
			digest: error.digest,
			message: error.message,
			timestamp: new Date().toISOString(),
			tags: ["control", "agent-runtime", "sessions"],
		});
	}, [error]);

	return (
		<div className="h-full w-full flex items-center justify-center bg-black/60 backdrop-blur-xl p-8">
			<motion.div
				initial={{ opacity: 0, scale: 0.95, y: 10 }}
				animate={{ opacity: 1, scale: 1, y: 0 }}
				transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
				className="max-w-xl w-full"
			>
				<Card className="bg-zinc-950/40 border-destructive/20 rounded-[3rem] shadow-[0_30px_60px_-15px_rgba(220,38,38,0.2)] overflow-hidden relative backdrop-blur-3xl">
					<div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-destructive to-transparent opacity-50" />

					<CardHeader className="flex flex-col items-center text-center pt-14 pb-8">
						<div className="h-24 w-24 bg-destructive/5 rounded-[2rem] flex items-center justify-center mb-8 border border-destructive/10 relative overflow-hidden group">
							<div className="absolute inset-0 bg-destructive/5 group-hover:bg-destructive/10 transition-colors" />
							<div className="absolute inset-0 bg-destructive/10 animate-pulse rounded-2xl opacity-40 scale-125 blur-xl" />
							<SlidersHorizontal
								className="h-10 w-10 text-destructive relative z-10"
								strokeWidth={1}
							/>
						</div>
						<CardTitle className="text-3xl font-black uppercase tracking-tight mb-3 text-white">
							Control Surface Fault
						</CardTitle>
						<CardDescription className="max-w-[320px] text-zinc-500 text-sm leading-relaxed">
							The agent runtime control surface encountered an error. Running sessions are
							unaffected.
						</CardDescription>
					</CardHeader>

					<CardContent className="px-12 pb-14 flex flex-col items-center">
						<div className="w-full bg-white/[0.02] rounded-2xl p-6 mb-10 border border-white/5 flex items-start gap-4 shadow-inner">
							<Activity className="h-5 w-5 text-destructive/30 shrink-0 mt-1" />
							<div className="flex flex-col gap-1">
								<span className="text-[9px] font-black uppercase tracking-widest text-zinc-600">
									Error Log
								</span>
								<code className="text-[11px] font-mono text-zinc-400 break-all leading-relaxed">
									{error.message ?? "Unhandled exception in ControlPage"}
								</code>
							</div>
						</div>

						<div className="flex flex-col w-full gap-4">
							<Button
								variant="outline"
								size="lg"
								disabled={isPending}
								onClick={() => startTransition(() => reset())}
								className="h-16 rounded-2xl border-destructive/30 text-destructive hover:bg-destructive/10 hover:border-destructive/40 font-bold text-base transition-all active:scale-95 shadow-lg shadow-destructive/5"
							>
								<RefreshCcw className={`mr-3 h-5 w-5 ${isPending ? "animate-spin" : ""}`} />
								{isPending ? "Reloading Control Surface..." : "Reset Control Surface"}
							</Button>

							<div className="flex items-center justify-center gap-6 mt-2">
								<button
									onClick={() => window.location.reload()}
									className="text-zinc-600 hover:text-white text-[10px] font-black uppercase tracking-[0.2em] transition-all"
								>
									Hard Reload
								</button>
								<div className="h-1 w-1 bg-zinc-800 rounded-full" />
								<span className="text-[10px] text-zinc-800 font-mono">
									{error.digest ?? "0x000000"}
								</span>
							</div>
						</div>
					</CardContent>
				</Card>
			</motion.div>
		</div>
	);
}
