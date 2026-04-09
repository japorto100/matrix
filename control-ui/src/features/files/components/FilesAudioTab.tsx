"use client";

// DW7 tab wrapper — audio tab
// Shows list of audio files; on select loads presigned URL into AudioPlayer.

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Music } from "lucide-react";
import { useState } from "react";
import { getErrorMessage } from "@/lib/utils";
import { AudioPlayer } from "./AudioPlayer";

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

async function fetchUrl(id: string): Promise<string> {
	const res = await fetch(`/api/files/${encodeURIComponent(id)}/url`, { cache: "no-store" });
	if (!res.ok) throw new Error("NO_DOCUMENT_INDEX");
	const d = (await res.json()) as { url: string };
	return d.url;
}

export function FilesAudioTab() {
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

	const { data: audioUrl } = useQuery<string, Error>({
		queryKey: ["file-url", selectedId],
		queryFn: () => fetchUrl(selectedId!),
		enabled: !!selectedId,
		staleTime: 10 * 60 * 1000,
	});

	const files = (data?.recent_uploads ?? []).filter((f) =>
		["mp3", "wav", "opus", "audio"].includes(f.type),
	);
	const selectedFile = files.find((f) => f.id === selectedId);

	return (
		<div className="flex h-full min-h-0">
			{/* File list */}
			<div className="w-56 shrink-0 flex flex-col gap-2 border-r border-border p-3 overflow-y-auto">
				<p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
					Audio Files
				</p>

				{isLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
				{isError && (
					<div className="flex items-center gap-1.5 text-destructive text-xs">
						<AlertTriangle className="h-3.5 w-3.5" />
						<span className="font-mono">{getErrorMessage(error)}</span>
					</div>
				)}
				{!isLoading && files.length === 0 && (
					<p className="text-xs text-muted-foreground/60 italic">No audio files yet.</p>
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
						<Music className="h-3.5 w-3.5 shrink-0" />
						<span className="truncate">{f.name}</span>
					</button>
				))}
			</div>

			{/* Player */}
			<div className="flex flex-1 flex-col p-4 gap-4">
				{!selectedFile ? (
					<div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
						<Music className="h-8 w-8 text-muted-foreground/30" />
						<p className="text-sm">Select an audio file to play</p>
					</div>
				) : audioUrl ? (
					<AudioPlayer url={audioUrl} title={selectedFile.name} />
				) : (
					<div className="flex items-center gap-2 text-muted-foreground text-sm">
						<Loader2 className="h-4 w-4 animate-spin" />
						Loading audio…
					</div>
				)}
			</div>
		</div>
	);
}
