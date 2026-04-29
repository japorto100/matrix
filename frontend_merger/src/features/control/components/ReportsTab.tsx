"use client";

import {
	AlertTriangle,
	CheckCircle2,
	ExternalLink,
	FileText,
	Hash,
	Link2,
	ShieldCheck,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useReportArtifacts } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { mockReportArtifacts } from "../mock-data";
import type { ReportArtifact } from "../types";

const STATUS_COLOR: Record<ReportArtifact["status"], string> = {
	generated: "border-sky-500/40 text-sky-400",
	validated: "border-emerald-500/40 text-emerald-400",
	failed: "border-rose-500/40 text-rose-400",
	published: "border-purple-500/40 text-purple-400",
};

const PUBLICATION_COLOR: Record<
	NonNullable<ReportArtifact["matrix_publication"]>["status"],
	string
> = {
	not_published: "border-border text-muted-foreground",
	ready: "border-sky-500/40 text-sky-400",
	published: "border-emerald-500/40 text-emerald-400",
	blocked: "border-rose-500/40 text-rose-400",
};

function formatTimestamp(value: string): string {
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	return date.toLocaleString(undefined, {
		month: "short",
		day: "2-digit",
		hour: "2-digit",
		minute: "2-digit",
	});
}

function matchesReport(report: ReportArtifact, query: string): boolean {
	return [
		report.report_id,
		report.title,
		report.owner,
		report.renderer,
		report.manifest_path,
		...report.input_sources,
		...report.citations.map((citation) => citation.title),
		...report.citations.map((citation) => citation.source_id),
		...report.output_files.map((file) => file.path),
	]
		.join(" ")
		.toLowerCase()
		.includes(query);
}

export function ReportsTab() {
	const [filter, setFilter] = useState("");
	const query = useReportArtifacts();
	const reports = (query.data?.items as ReportArtifact[] | undefined) ?? mockReportArtifacts;
	const normalizedFilter = filter.trim().toLowerCase();
	const filtered = useMemo(() => {
		if (!normalizedFilter) return reports;
		return reports.filter((report) => matchesReport(report, normalizedFilter));
	}, [normalizedFilter, reports]);
	const validReports = reports.filter((report) => report.validation.passed).length;
	const outputCount = reports.reduce((acc, report) => acc + report.output_files.length, 0);
	const citationCount = reports.reduce((acc, report) => acc + report.citations.length, 0);
	const matrixReady = reports.filter(
		(report) =>
			report.matrix_publication?.status === "ready" ||
			report.matrix_publication?.status === "published",
	).length;

	return (
		<div className="px-6 py-4 space-y-4">
			<header className="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h2 className="text-base font-semibold">Report Artifacts</h2>
					<p className="text-xs text-muted-foreground">
						{reports.length} reports · {validReports} valid · {outputCount} outputs
					</p>
				</div>
				<Input
					placeholder="Filter reports, citations, manifests..."
					value={filter}
					onChange={(event) => setFilter(event.target.value)}
					className="h-8 w-full text-xs sm:w-80"
				/>
			</header>

			<div className="grid grid-cols-1 gap-3 md:grid-cols-4">
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Validated</span>
						<ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">
						{validReports}/{reports.length}
					</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Citations</span>
						<Link2 className="h-3.5 w-3.5 text-sky-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">{citationCount}</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Outputs</span>
						<FileText className="h-3.5 w-3.5 text-purple-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">{outputCount}</div>
				</div>
				<div className="rounded-lg border border-border bg-card/30 p-3">
					<div className="flex items-center justify-between gap-2">
						<span className="text-[11px] text-muted-foreground">Matrix Ready</span>
						<ExternalLink className="h-3.5 w-3.5 text-amber-400" />
					</div>
					<div className="mt-2 text-lg font-semibold">{matrixReady}</div>
				</div>
			</div>

			<div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
				{filtered.map((report) => {
					const publicationStatus = report.matrix_publication?.status ?? "not_published";
					return (
						<Card key={report.report_id}>
							<CardHeader className="pb-3">
								<div className="flex flex-wrap items-start justify-between gap-3">
									<div className="min-w-0">
										<CardTitle className="truncate text-sm">{report.title}</CardTitle>
										<p className="mt-1 font-mono text-[10px] text-muted-foreground">
											{report.report_id}
										</p>
									</div>
									<div className="flex flex-wrap gap-1">
										<Badge
											variant="outline"
											className={cn("h-5 px-1.5 text-[10px]", STATUS_COLOR[report.status])}
										>
											{report.status}
										</Badge>
										<Badge
											variant="outline"
											className={cn("h-5 px-1.5 text-[10px]", PUBLICATION_COLOR[publicationStatus])}
										>
											{publicationStatus}
										</Badge>
									</div>
								</div>
							</CardHeader>
							<CardContent className="space-y-3">
								<div className="grid grid-cols-2 gap-2 text-xs">
									<div>
										<p className="text-[10px] uppercase text-muted-foreground/70">Renderer</p>
										<p className="font-mono">{report.renderer}</p>
									</div>
									<div>
										<p className="text-[10px] uppercase text-muted-foreground/70">Generated</p>
										<p className="font-mono">{formatTimestamp(report.generated_at)}</p>
									</div>
									<div>
										<p className="text-[10px] uppercase text-muted-foreground/70">Owner</p>
										<p className="font-mono">{report.owner}</p>
									</div>
									<div>
										<p className="text-[10px] uppercase text-muted-foreground/70">Version</p>
										<p className="font-mono">{report.renderer_version}</p>
									</div>
								</div>

								<div className="rounded border border-border/50 p-2">
									<div className="flex items-center gap-1 text-[10px] uppercase text-muted-foreground/70">
										<Hash className="h-3 w-3" />
										Manifest
									</div>
									<p className="mt-1 truncate font-mono text-[11px]">{report.manifest_path}</p>
									<p className="mt-1 truncate font-mono text-[10px] text-muted-foreground">
										{report.checksum || "checksum pending"}
									</p>
								</div>

								<div>
									<p className="mb-1 text-[10px] uppercase text-muted-foreground/70">Outputs</p>
									<div className="flex flex-wrap gap-1">
										{report.output_files.map((file) => (
											<Badge
												key={`${report.report_id}-${file.path}`}
												variant="secondary"
												className="h-4 px-1.5 text-[9px]"
											>
												{file.kind}: {file.path}
											</Badge>
										))}
									</div>
								</div>

								<div>
									<p className="mb-1 text-[10px] uppercase text-muted-foreground/70">Citations</p>
									<div className="space-y-1">
										{report.citations.map((citation) => (
											<div
												key={`${report.report_id}-${citation.citation_id}`}
												className="rounded border border-border/50 px-2 py-1"
											>
												<div className="flex items-center justify-between gap-2">
													<p className="truncate text-xs">{citation.title}</p>
													<Badge variant="secondary" className="h-4 px-1.5 text-[9px]">
														{citation.source_type}
													</Badge>
												</div>
												<p className="truncate font-mono text-[10px] text-muted-foreground">
													{citation.citation_id} · {citation.source_id}
												</p>
											</div>
										))}
									</div>
								</div>

								{report.validation.passed ? (
									<div className="flex items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/10 p-2 text-xs text-emerald-300">
										<CheckCircle2 className="h-3.5 w-3.5" />
										Manifest validation passed
									</div>
								) : (
									<div className="rounded border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-300">
										<div className="mb-1 flex items-center gap-1">
											<AlertTriangle className="h-3.5 w-3.5" />
											Validation failed
										</div>
										<p className="font-mono text-[10px]">{report.validation.failures.join(", ")}</p>
									</div>
								)}
							</CardContent>
						</Card>
					);
				})}
			</div>

			{filtered.length === 0 && (
				<div className="rounded-lg border border-dashed border-border py-8 text-center text-xs text-muted-foreground">
					No report artifacts match filters
				</div>
			)}
		</div>
	);
}
