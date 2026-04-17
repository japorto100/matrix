"use client";

// Files Overview Tab — DW5
// Shows: total docs, indexing status, recent uploads, failed jobs.
// v1: read-only, BFF-driven via /api/files. Degradation visible on fetch error.

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Clock, FileText, Loader2, UploadCloud } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface FilesOverviewData {
	total_documents: number;
	indexing_pending: number;
	indexing_failed: number;
	recent_uploads: Array<{
		id: string;
		name: string;
		type: string;
		status: string;
		created_at: string;
	}>;
}

async function fetchFilesOverview(): Promise<FilesOverviewData> {
	const res = await fetch("/api/files", { cache: "no-store" });
	if (!res.ok) {
		const err = (await res.json().catch(() => ({}))) as { code?: string };
		throw new Error(err.code ?? "STORAGE_UNAVAILABLE");
	}
	return res.json() as Promise<FilesOverviewData>;
}

function StatusBadge({ status }: { status: string }) {
	if (status === "indexed") {
		return (
			<Badge variant="outline" className="border-emerald-500/50 text-emerald-500 text-[10px]">
				<CheckCircle2 className="h-3 w-3 mr-1" />
				indexed
			</Badge>
		);
	}
	if (status === "pending" || status === "processing") {
		return (
			<Badge variant="outline" className="border-amber-500/50 text-amber-500 text-[10px]">
				<Loader2 className="h-3 w-3 mr-1 animate-spin" />
				{status}
			</Badge>
		);
	}
	if (status === "failed") {
		return (
			<Badge variant="outline" className="border-red-500/50 text-red-500 text-[10px]">
				<AlertTriangle className="h-3 w-3 mr-1" />
				failed
			</Badge>
		);
	}
	return (
		<Badge variant="outline" className="text-[10px]">
			{status}
		</Badge>
	);
}

export function FilesOverviewTab() {
	const { data, isLoading, isError, error } = useQuery<FilesOverviewData, Error>({
		queryKey: ["files-overview"],
		queryFn: fetchFilesOverview,
		staleTime: 30_000,
		retry: 1,
	});

	if (isLoading) {
		return (
			<div className="flex flex-1 items-center justify-center gap-2 p-8 text-muted-foreground">
				<Loader2 className="h-4 w-4 animate-spin" />
				<span className="text-sm">Loading files…</span>
			</div>
		);
	}

	if (isError) {
		const code = error?.message ?? "STORAGE_UNAVAILABLE";
		return (
			<div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
				<AlertTriangle className="h-6 w-6 text-destructive" />
				<p className="text-sm font-medium text-destructive">Files unavailable</p>
				<p className="text-xs font-mono text-muted-foreground">{code}</p>
			</div>
		);
	}

	const overview = data ?? {
		total_documents: 0,
		indexing_pending: 0,
		indexing_failed: 0,
		recent_uploads: [],
	};

	return (
		<div className="flex flex-col gap-4 p-4">
			{/* Stats row */}
			<div className="grid grid-cols-3 gap-3">
				<Card className="gap-0 py-0">
					<CardHeader className="pb-1 pt-3 px-4">
						<CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
							Total Documents
						</CardTitle>
					</CardHeader>
					<CardContent className="px-4 pb-3">
						<div className="flex items-center gap-2">
							<FileText className="h-4 w-4 text-muted-foreground" />
							<span className="text-2xl font-bold">{overview.total_documents}</span>
						</div>
					</CardContent>
				</Card>

				<Card className="gap-0 py-0">
					<CardHeader className="pb-1 pt-3 px-4">
						<CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
							Indexing Pending
						</CardTitle>
					</CardHeader>
					<CardContent className="px-4 pb-3">
						<div className="flex items-center gap-2">
							<Clock className="h-4 w-4 text-amber-500" />
							<span className="text-2xl font-bold">{overview.indexing_pending}</span>
						</div>
					</CardContent>
				</Card>

				<Card className="gap-0 py-0">
					<CardHeader className="pb-1 pt-3 px-4">
						<CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
							Failed Jobs
						</CardTitle>
					</CardHeader>
					<CardContent className="px-4 pb-3">
						<div className="flex items-center gap-2">
							<AlertTriangle
								className={`h-4 w-4 ${overview.indexing_failed > 0 ? "text-destructive" : "text-muted-foreground"}`}
							/>
							<span className="text-2xl font-bold">{overview.indexing_failed}</span>
						</div>
					</CardContent>
				</Card>
			</div>

			{/* Recent uploads */}
			<Card className="gap-0 py-0">
				<CardHeader className="pb-2 pt-3 px-4">
					<CardTitle className="text-xs text-muted-foreground font-medium uppercase tracking-wider flex items-center gap-2">
						<UploadCloud className="h-3.5 w-3.5" />
						Recent Uploads
					</CardTitle>
				</CardHeader>
				<CardContent className="px-4 pb-3">
					{overview.recent_uploads.length === 0 ? (
						<p className="text-xs text-muted-foreground/60 italic">No uploads yet.</p>
					) : (
						<div className="flex flex-col divide-y divide-border/50">
							{overview.recent_uploads.map((file) => (
								<div key={file.id} className="flex items-center justify-between gap-2 py-1.5">
									<div className="flex items-center gap-2 min-w-0">
										<FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
										<span className="text-xs truncate font-medium">{file.name}</span>
										<span className="text-[10px] text-muted-foreground shrink-0 font-mono uppercase">
											{file.type}
										</span>
									</div>
									<div className="flex items-center gap-2 shrink-0">
										<StatusBadge status={file.status} />
										<span className="text-[10px] text-muted-foreground/60 font-mono">
											{new Date(file.created_at).toLocaleDateString()}
										</span>
									</div>
								</div>
							))}
						</div>
					)}
				</CardContent>
			</Card>
		</div>
	);
}
