"use client";

// TasksTab — exec-scheduler Lane D
// List / pause / resume / cancel / delete user's scheduled tasks.
// NO Add-Task form — creation happens in agent-chat / matrix-DM (chat-first).
// Uses /api/scheduler BFF proxy → Go-appservice /api/v1/scheduler.

import { Calendar, CheckCircle2, Clock, Pause, Play, Trash2, XCircle } from "lucide-react";
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
import { useDeleteTask, usePatchTask, useScheduledTasks, useTaskRuns } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import type { ScheduledTask, ScheduledTaskStatus, TaskExecution } from "../types";

function formatRelative(ms?: number): string {
	if (!ms) return "—";
	const diff = Date.now() - ms;
	const minutes = Math.floor(diff / 60_000);
	if (minutes < 1) return "just now";
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	return `${Math.floor(hours / 24)}d ago`;
}

function formatTrigger(task: ScheduledTask): string {
	if (task.cron_expr) return task.cron_expr;
	if (task.scheduled_at_ms) {
		return new Date(task.scheduled_at_ms).toLocaleString();
	}
	return "—";
}

function statusBadgeVariant(
	status: ScheduledTaskStatus,
): "default" | "secondary" | "destructive" | "outline" {
	switch (status) {
		case "active":
			return "default";
		case "paused":
			return "secondary";
		case "cancelled":
		case "errored":
			return "destructive";
		case "completed":
			return "outline";
		default:
			return "outline";
	}
}

export function TasksTab() {
	// TODO(auth): user_id="local" is the Control-surface placeholder —
	// same pattern as useOverview() / useContextInspector(). When the
	// app gets real session-aware userId wiring (BFF cookie or client-
	// side session provider), replace this one constant in one sweep.
	const userId = "local";
	const query = useScheduledTasks(userId);
	const tasks = (query.data?.tasks as ScheduledTask[] | undefined) ?? [];
	const patch = usePatchTask(userId);
	const del = useDeleteTask(userId);

	const [drawerTask, setDrawerTask] = useState<ScheduledTask | null>(null);
	const [confirmDelete, setConfirmDelete] = useState<ScheduledTask | null>(null);

	const handlePause = async (task: ScheduledTask) => {
		try {
			await patch.mutateAsync({ taskId: task.task_id, status: "paused" });
			toast.success(`Paused ${task.task_id.slice(0, 8)}`);
		} catch (err) {
			toast.error(`Pause failed: ${errMsg(err)}`);
		}
	};

	const handleResume = async (task: ScheduledTask) => {
		try {
			await patch.mutateAsync({ taskId: task.task_id, status: "active" });
			toast.success(`Resumed ${task.task_id.slice(0, 8)}`);
		} catch (err) {
			toast.error(`Resume failed: ${errMsg(err)}`);
		}
	};

	const handleCancel = async (task: ScheduledTask) => {
		try {
			await patch.mutateAsync({ taskId: task.task_id, status: "cancelled" });
			toast.success(`Cancelled ${task.task_id.slice(0, 8)}`);
		} catch (err) {
			toast.error(`Cancel failed: ${errMsg(err)}`);
		}
	};

	const handleDelete = async () => {
		if (!confirmDelete) return;
		try {
			await del.mutateAsync(confirmDelete.task_id);
			toast.success(`Deleted ${confirmDelete.task_id.slice(0, 8)}`);
			setConfirmDelete(null);
		} catch (err) {
			toast.error(`Delete failed: ${errMsg(err)}`);
		}
	};

	const active = tasks.filter((t) => t.status === "active").length;
	const paused = tasks.filter((t) => t.status === "paused").length;

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex items-baseline justify-between">
				<div>
					<h2 className="text-base font-semibold">Scheduled Tasks</h2>
					<p className="text-xs text-muted-foreground">
						{tasks.length} total · {active} active · {paused} paused
					</p>
				</div>
			</header>

			{tasks.length === 0 ? (
				<EmptyState />
			) : (
				<div className="grid gap-2">
					{tasks.map((task) => (
						<TaskRow
							key={task.task_id}
							task={task}
							onPause={handlePause}
							onResume={handleResume}
							onCancel={handleCancel}
							onDelete={(t) => setConfirmDelete(t)}
							onShowRuns={(t) => setDrawerTask(t)}
						/>
					))}
				</div>
			)}

			<TaskRunsDrawer userId={userId} task={drawerTask} onClose={() => setDrawerTask(null)} />

			<AlertDialog open={!!confirmDelete} onOpenChange={(open) => !open && setConfirmDelete(null)}>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle>Delete scheduled task?</AlertDialogTitle>
						<AlertDialogDescription>
							This permanently removes{" "}
							<code className="font-mono text-foreground">
								{confirmDelete?.task_id.slice(0, 16)}
							</code>{" "}
							and all its execution history. Use <em>cancel</em> instead if you want to keep the
							audit trail.
						</AlertDialogDescription>
					</AlertDialogHeader>
					<AlertDialogFooter>
						<AlertDialogCancel>Cancel</AlertDialogCancel>
						<AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</div>
	);
}

function TaskRow({
	task,
	onPause,
	onResume,
	onCancel,
	onDelete,
	onShowRuns,
}: {
	task: ScheduledTask;
	onPause: (t: ScheduledTask) => void;
	onResume: (t: ScheduledTask) => void;
	onCancel: (t: ScheduledTask) => void;
	onDelete: (t: ScheduledTask) => void;
	onShowRuns: (t: ScheduledTask) => void;
}) {
	const isActive = task.status === "active";
	const isPaused = task.status === "paused";
	const isTerminal =
		task.status === "completed" || task.status === "cancelled" || task.status === "errored";

	return (
		<Card className="py-3">
			<CardHeader className="py-0 px-4 flex-row items-baseline justify-between gap-4">
				<div className="flex-1 min-w-0">
					<div className="flex items-center gap-2">
						<CardTitle className="text-sm font-medium">
							{task.prompt?.slice(0, 80) || "(no prompt)"}
						</CardTitle>
						<Badge variant={statusBadgeVariant(task.status)} className="text-[10px]">
							{task.status}
						</Badge>
						<Badge variant="outline" className="text-[10px]">
							{task.kind}
						</Badge>
					</div>
					<p className="text-xs text-muted-foreground mt-1 flex items-center gap-3">
						<span className="inline-flex items-center gap-1">
							<Calendar className="h-3 w-3" />
							{formatTrigger(task)} · {task.tz}
						</span>
						<span className="inline-flex items-center gap-1">
							<Clock className="h-3 w-3" />
							last run {formatRelative(task.last_run_at_ms)}
						</span>
						<span className="text-muted-foreground/60">{task.execution_count} fires</span>
					</p>
				</div>
				<div className="flex gap-1 shrink-0">
					<Button size="sm" variant="ghost" onClick={() => onShowRuns(task)}>
						Runs
					</Button>
					{isActive && (
						<Button size="sm" variant="ghost" onClick={() => onPause(task)} aria-label="Pause">
							<Pause className="h-3.5 w-3.5" />
						</Button>
					)}
					{isPaused && (
						<Button size="sm" variant="ghost" onClick={() => onResume(task)} aria-label="Resume">
							<Play className="h-3.5 w-3.5" />
						</Button>
					)}
					{!isTerminal && (
						<Button size="sm" variant="ghost" onClick={() => onCancel(task)} aria-label="Cancel">
							<XCircle className="h-3.5 w-3.5" />
						</Button>
					)}
					<Button size="sm" variant="ghost" onClick={() => onDelete(task)} aria-label="Delete">
						<Trash2 className="h-3.5 w-3.5 text-destructive" />
					</Button>
				</div>
			</CardHeader>
		</Card>
	);
}

function TaskRunsDrawer({
	userId,
	task,
	onClose,
}: {
	userId: string;
	task: ScheduledTask | null;
	onClose: () => void;
}) {
	const { data } = useTaskRuns(userId, task?.task_id ?? null);
	const runs = (data?.runs as TaskExecution[] | undefined) ?? [];
	if (!task) return null;
	return (
		<div className="fixed inset-y-0 right-0 w-[420px] bg-background border-l shadow-lg z-50 overflow-auto">
			<div className="p-4 border-b flex items-center justify-between">
				<div>
					<h3 className="text-sm font-semibold">Runs</h3>
					<p className="text-xs text-muted-foreground font-mono">{task.task_id.slice(0, 16)}</p>
				</div>
				<Button size="sm" variant="ghost" onClick={onClose}>
					Close
				</Button>
			</div>
			<div className="p-4 space-y-2">
				{runs.length === 0 ? (
					<p className="text-xs text-muted-foreground">No runs yet.</p>
				) : (
					runs.map((r) => <RunRow key={r.execution_id} run={r} />)
				)}
			</div>
		</div>
	);
}

function RunRow({ run }: { run: TaskExecution }) {
	const icon =
		run.status === "completed" ? (
			<CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
		) : run.status === "failed" || run.status === "timeout" ? (
			<XCircle className="h-3.5 w-3.5 text-destructive" />
		) : (
			<Clock className="h-3.5 w-3.5 text-muted-foreground" />
		);

	return (
		<Card className={cn("py-2")}>
			<CardContent className="py-0 px-3">
				<div className="flex items-center gap-2 text-xs">
					{icon}
					<span className="font-medium">{run.status}</span>
					<span className="text-muted-foreground ml-auto font-mono text-[10px]">
						{formatRelative(run.started_at)}
					</span>
				</div>
				{run.result_summary && (
					<p className="text-xs text-muted-foreground mt-1">{run.result_summary}</p>
				)}
				{run.error && <p className="text-xs text-destructive mt-1">{run.error}</p>}
				{run.duration_ms ? (
					<p className="text-[10px] text-muted-foreground/70 mt-1">{run.duration_ms}ms</p>
				) : null}
			</CardContent>
		</Card>
	);
}

function EmptyState() {
	return (
		<Card>
			<CardContent className="py-10 text-center space-y-2">
				<p className="text-sm font-medium">No scheduled tasks yet</p>
				<p className="text-xs text-muted-foreground max-w-sm mx-auto">
					Create one by chatting with the agent — e.g.{" "}
					<em className="font-mono">"jeden Montag um 9 ein Portfolio-Briefing"</em>, or DM{" "}
					<code className="font-mono text-foreground">@agent:matrix.local</code> and describe what
					you want.
				</p>
				<div className="pt-2 flex items-center justify-center gap-2">
					<a href="/agent" className="text-xs underline text-primary hover:text-primary/80">
						Open Agent Chat
					</a>
					<span className="text-xs text-muted-foreground">·</span>
					<a href="/matrix" className="text-xs underline text-primary hover:text-primary/80">
						Open Matrix
					</a>
				</div>
			</CardContent>
		</Card>
	);
}

function errMsg(err: unknown): string {
	return err instanceof Error ? err.message : "unknown";
}
