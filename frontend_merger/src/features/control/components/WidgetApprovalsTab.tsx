"use client";

import {
	AlertTriangle,
	CheckCircle2,
	ExternalLink,
	FileText,
	ShieldCheck,
	XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useWidgetProposals } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockWidgetProposals } from "../mock-data";
import type { MatrixWidgetApprovalItem, MatrixWidgetApprovalStatus } from "../types";

const STATUS_COLOR: Record<MatrixWidgetApprovalStatus, string> = {
	pending: "border-amber-500/40 text-amber-400",
	approved: "border-emerald-500/40 text-emerald-400",
	blocked: "border-rose-500/40 text-rose-400",
	denied: "border-zinc-500/40 text-zinc-400",
	revoked: "border-zinc-500/40 text-zinc-400",
};

export function filterWidgetProposals(
	items: MatrixWidgetApprovalItem[],
	filter: string,
	status: string,
): MatrixWidgetApprovalItem[] {
	const normalized = filter.trim().toLowerCase();
	return items.filter((item) => {
		const statusMatches = status === "all" || item.status === status;
		if (!statusMatches) return false;
		if (!normalized) return true;
		return [
			item.proposal_id,
			item.report_id,
			item.title,
			item.room_id,
			item.requester_user_id,
			item.url,
			item.resource_uri,
			item.report_artifact?.manifest_id,
			item.report_artifact?.output_path,
			...item.denial_reasons,
			...item.audit_refs,
		]
			.filter(Boolean)
			.join(" ")
			.toLowerCase()
			.includes(normalized);
	});
}

export function WidgetApprovalsTab() {
	const [filter, setFilter] = useState("");
	const [statusFilter, setStatusFilter] = useState("all");
	const query = useWidgetProposals();
	const proposals = query.data?.items ?? mockWidgetProposals;
	const filtered = useMemo(
		() => filterWidgetProposals(proposals, filter, statusFilter),
		[filter, proposals, statusFilter],
	);
	const pending = proposals.filter((item) => item.status === "pending").length;
	const approved = proposals.filter((item) => item.status === "approved").length;
	const blocked = proposals.filter((item) => item.status === "blocked").length;

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h2 className="text-base font-semibold">Matrix Widget Approvals</h2>
					<p className="text-xs text-muted-foreground">
						{proposals.length} proposals · {pending} pending · {blocked} blocked
					</p>
				</div>
				<div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
					<select
						value={statusFilter}
						onChange={(event) => setStatusFilter(event.target.value)}
						className="h-8 rounded border border-border bg-background px-2 text-xs"
					>
						<option value="all">All status</option>
						<option value="pending">Pending</option>
						<option value="approved">Approved</option>
						<option value="blocked">Blocked</option>
						<option value="denied">Denied</option>
						<option value="revoked">Revoked</option>
					</select>
					<Input
						placeholder="Filter widgets, rooms, reports..."
						value={filter}
						onChange={(event) => setFilter(event.target.value)}
						className="h-8 w-full text-xs sm:w-80"
					/>
				</div>
			</header>

			<div className="grid grid-cols-1 gap-3 md:grid-cols-4">
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Pending</span>
						<AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">{pending}</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Approved</span>
						<CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">{approved}</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Blocked</span>
						<XCircle className="h-3.5 w-3.5 text-rose-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">{blocked}</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Contract</span>
						<ShieldCheck className="h-3.5 w-3.5 text-sky-400" />
					</div>
					<div className="mt-2 truncate font-mono text-xs">
						{query.data?.contract ?? "matrix-widget-approval/v1"}
					</div>
				</div>
			</div>

			<div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
				{filtered.map((proposal) => (
					<Card key={proposal.proposal_id}>
						<CardHeader className="pb-3">
							<div className="flex flex-wrap items-start justify-between gap-3">
								<div className="min-w-0">
									<CardTitle className="truncate text-sm">{proposal.title}</CardTitle>
									<p className="mt-1 truncate font-mono text-[10px] text-muted-foreground">
										{proposal.proposal_id}
									</p>
								</div>
								<Badge
									variant="outline"
									className={cn("h-5 px-1.5 text-[10px]", STATUS_COLOR[proposal.status])}
								>
									{proposal.status}
								</Badge>
							</div>
						</CardHeader>
						<CardContent className="space-y-3">
							<div className="grid grid-cols-2 gap-2 text-xs">
								<div>
									<p className="text-[10px] uppercase text-muted-foreground/70">Room</p>
									<p className="truncate font-mono">{proposal.room_id}</p>
								</div>
								<div>
									<p className="text-[10px] uppercase text-muted-foreground/70">Requester</p>
									<p className="truncate font-mono">{proposal.requester_user_id}</p>
								</div>
							</div>

							<div className="rounded border border-border/50 p-2">
								<div className="flex items-center gap-1 text-[10px] uppercase text-muted-foreground/70">
									<FileText className="h-3 w-3" />
									Report Artifact
								</div>
								<p className="mt-1 truncate font-mono text-[11px]">
									{proposal.report_artifact?.manifest_id ?? "n/a"}
								</p>
								<p className="mt-1 truncate font-mono text-[10px] text-muted-foreground">
									{proposal.report_artifact?.output_path ?? "output pending"}
								</p>
							</div>

							{proposal.url && (
								<a
									href={proposal.url}
									target="_blank"
									rel="noreferrer"
									className="flex items-center gap-1 truncate rounded border border-border/50 px-2 py-1.5 font-mono text-[11px] text-sky-300 hover:bg-accent"
								>
									<ExternalLink className="h-3 w-3 shrink-0" />
									<span className="truncate">{proposal.url}</span>
								</a>
							)}

							<div className="flex flex-wrap gap-1">
								{proposal.permissions.map((permission) => (
									<Badge key={permission} variant="secondary" className="h-4 px-1.5 text-[9px]">
										{permission}
									</Badge>
								))}
								{proposal.audit_refs.map((auditRef) => (
									<Badge key={auditRef} variant="outline" className="h-4 px-1.5 text-[9px]">
										audit {auditRef}
									</Badge>
								))}
							</div>

							{proposal.denial_reasons.length > 0 && (
								<div className="rounded border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-300">
									<div className="mb-1 flex items-center gap-1">
										<AlertTriangle className="h-3.5 w-3.5" />
										Policy
									</div>
									<p className="font-mono text-[10px]">{proposal.denial_reasons.join(", ")}</p>
								</div>
							)}

							<div className="flex flex-wrap justify-end gap-2">
								<Button
									variant="outline"
									size="sm"
									className="h-8 gap-1.5 text-xs"
									disabled={!proposal.can_deny}
								>
									<XCircle className="h-3 w-3" />
									Deny
								</Button>
								<Button size="sm" className="h-8 gap-1.5 text-xs" disabled={!proposal.can_approve}>
									<CheckCircle2 className="h-3 w-3" />
									Approve
								</Button>
							</div>
						</CardContent>
					</Card>
				))}
			</div>

			{filtered.length === 0 && (
				<div className="rounded-lg border border-dashed border-border py-8 text-center text-xs text-muted-foreground">
					No widget proposals match filters
				</div>
			)}
		</div>
	);
}
