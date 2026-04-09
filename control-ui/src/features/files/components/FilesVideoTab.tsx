"use client";

// DW8 tab wrapper — video tab

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Video } from "lucide-react";
import { useState } from "react";
import { getErrorMessage } from "@/lib/utils";
import { VideoPlayer } from "./VideoPlayer";

interface FileRecord {
	id: string;
	name: string;
	type: string;
	status: string;
	created_at: string;
}

interface FilesListResponse {
	recent_uploads: FileRecord[];
}

export function FilesVideoTab() {
	const [selectedId, setSelectedId] = useState<string | null>(null);

	const { data, isLoading, isError, error } = useQuery<FilesListResponse, Error>({
		queryKey: ["files-list"],
		queryFn: async () => {
			const res = await fetch("/api/files", { cache: "no-store" });
			if (!res.ok) throw new Error("STORAGE_UNAVAILABLE");
			return res.json() as Promise<FilesListResponse>;
		},
		staleTime: 30_000,
	});

	const { data: videoUrl } = useQuery<string, Error>({
		queryKey: ["file-url", selectedId],
		queryFn: async () => {
			const res = await fetch(`/api/files/${encodeURIComponent(selectedId!)}/url`, {
				cache: "no-store",
			});
			if (!res.ok) throw new Error("NO_DOCUMENT_INDEX");
			const d = (await res.json()) as { url: string };
			return d.url;
		},
		enabled: !!selectedId,
		staleTime: 10 * 60 * 1000,
	});

	const files = (data?.recent_uploads ?? []).filter((f) =>
		["mp4", "webm", "hls", "video"].includes(f.type),
	);
	const selectedFile = files.find((f) => f.id === selectedId);

	return (
		<div className="flex h-full min-h-0">
			<div className="w-56 shrink-0 flex flex-col gap-2 border-r border-border p-3 overflow-y-auto">
				<p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
					Video Files
				</p>
				{isLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
				{isError && (
					<div className="flex items-center gap-1.5 text-destructive text-xs">
						<AlertTriangle className="h-3.5 w-3.5" />
						<span className="font-mono">{getErrorMessage(error)}</span>
					</div>
				)}
				{!isLoading && files.length === 0 && (
					<p className="text-xs text-muted-foreground/60 italic">No video files yet.</p>
				)}
				{files.map((f) => (
					<button
						key={f.id}
						onClick={() => setSelectedId(f.id)}
						className={`flex items-center gap-2 rounded px-2 py-1.5 text-left text-xs transition-colors ${
							f.id === selectedId
								? "bg-accent text-foreground"
								: "text-muted-foreground hover:bg-accent/50"
						}`}
					>
						<Video className="h-3.5 w-3.5 shrink-0" />
						<span className="truncate">{f.name}</span>
					</button>
				))}
			</div>

			<div className="flex flex-1 flex-col p-4 gap-4">
				{!selectedFile ? (
					<div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
						<Video className="h-8 w-8 text-muted-foreground/30" />
						<p className="text-sm">Select a video to play</p>
					</div>
				) : videoUrl ? (
					<VideoPlayer url={videoUrl} title={selectedFile.name} />
				) : (
					<div className="flex items-center gap-2 text-muted-foreground text-sm">
						<Loader2 className="h-4 w-4 animate-spin" />
						Loading video…
					</div>
				)}
			</div>
		</div>
	);
}
