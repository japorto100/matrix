"use client";

// SessionsTab — LangGraph thread checkpoints (exec-10)
// Slice 6.5 (NEU coverage gap): Sessions Browser
// K8 (Slice 6): Kill button (Dev Mode only) with AlertDialog confirmation

import { Activity, Clock, MessageCircle, Trash2, Wrench } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useKillSession, useSessions } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockSessions } from "../mock-data";
import { useControlMode } from "../mode";
import type { Session } from "../types";

function formatRelative(iso: string): string {
	const diffMs = Date.now() - new Date(iso).getTime();
	const minutes = Math.floor(diffMs / 60000);
	if (minutes < 1) return "just now";
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	return `${Math.floor(hours / 24)}d ago`;
}

export function SessionsTab() {
	// Slice 7 Phase H: real backend with mock fallback
	const query = useSessions();
	const sessions = (query.data?.items as Session[] | undefined) ?? mockSessions;
	const active = sessions.filter((s) => s.is_active).length;

	const { isDev } = useControlMode();
	const killSession = useKillSession();
	const [confirmKill, setConfirmKill] = useState<Session | null>(null);

	const handleConfirmKill = async () => {
		if (!confirmKill) return;
		try {
			await killSession.mutateAsync(confirmKill.thread_id);
			toast.success(`Killed session ${confirmKill.thread_id}`);
			setConfirmKill(null);
		} catch (err) {
			toast.error(`Kill failed: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold">Sessions</h2>
					<p className="text-xs text-muted-foreground">
						{sessions.length} threads · {active} active · LangGraph PG checkpointer
					</p>
				</div>
			</header>

			<AlertDialog open={!!confirmKill} onOpenChange={(open) => !open && setConfirmKill(null)}>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle>Kill session?</AlertDialogTitle>
						<AlertDialogDescription>
							This permanently deletes LangGraph checkpoints for thread{" "}
							<code className="font-mono text-foreground">{confirmKill?.thread_id}</code>. This
							action cannot be undone.
						</AlertDialogDescription>
					</AlertDialogHeader>
					<AlertDialogFooter>
						<AlertDialogCancel>Cancel</AlertDialogCancel>
						<AlertDialogAction
							onClick={handleConfirmKill}
							className="bg-rose-500 hover:bg-rose-600"
						>
							Kill Session
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>

			<div className="space-y-3">
				{sessions.map((session) => (
					<Card
						key={session.thread_id}
						className={cn(
							"cursor-pointer hover:border-accent transition-colors",
							session.is_active && "border-emerald-500/30 bg-emerald-950/5",
						)}
					>
						<CardHeader className="pb-2">
							<div className="flex items-start justify-between gap-3">
								<div className="flex items-center gap-2 flex-1 min-w-0">
									{session.is_active && (
										<div className="relative shrink-0">
											<div className="absolute inset-0 h-2 w-2 rounded-full bg-emerald-500/60 animate-ping" />
											<div className="relative h-2 w-2 rounded-full bg-emerald-500" />
										</div>
									)}
									<CardTitle className="text-sm font-mono leading-tight truncate">
										{session.thread_id}
									</CardTitle>
								</div>
								{session.role && (
									<Badge variant="secondary" className="text-[10px] capitalize shrink-0">
										{session.role.replace(/_/g, " ")}
									</Badge>
								)}
								{isDev && (
									<Button
										variant="ghost"
										size="sm"
										className="h-6 px-2 text-[10px] gap-1 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 shrink-0"
										onClick={(e) => {
											e.stopPropagation();
											setConfirmKill(session);
										}}
										disabled={killSession.isPending}
									>
										<Trash2 className="h-3 w-3" />
										Kill
									</Button>
								)}
							</div>
						</CardHeader>
						<CardContent className="space-y-2 pt-0">
							{session.last_message_preview && (
								<p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
									{session.last_message_preview}
								</p>
							)}
							<div className="flex items-center gap-3 text-[10px] text-muted-foreground">
								{session.message_count !== undefined && (
									<div className="flex items-center gap-1">
										<MessageCircle className="h-3 w-3" />
										{session.message_count} msgs
									</div>
								)}
								{session.tool_calls !== undefined && (
									<div className="flex items-center gap-1">
										<Wrench className="h-3 w-3" />
										{session.tool_calls} tool calls
									</div>
								)}
								{session.checkpoint_count !== undefined && session.message_count === undefined && (
									<div className="flex items-center gap-1">
										<MessageCircle className="h-3 w-3" />
										{session.checkpoint_count} checkpoints
									</div>
								)}
								{session.last_message_at && (
									<div className="flex items-center gap-1">
										<Clock className="h-3 w-3" />
										{formatRelative(session.last_message_at)}
									</div>
								)}
								{session.is_active && (
									<Badge
										variant="outline"
										className="text-[9px] h-4 border-emerald-500/50 text-emerald-400 gap-1 ml-auto"
									>
										<Activity className="h-2.5 w-2.5" />
										live
									</Badge>
								)}
							</div>
						</CardContent>
					</Card>
				))}
			</div>
		</div>
	);
}
