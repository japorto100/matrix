"use client";

// DW11 — UploadDropzone: react-dropzone v14 for files < 5MB
// bounded-write: audit fields required (DW18 — audit-log wired via BFF)
// v1.5: uppy v4 + tus for resumable > 5MB uploads

import { AlertTriangle, CheckCircle2, Loader2, UploadCloud } from "lucide-react";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { cn, getErrorMessage } from "@/lib/utils";

const ACCEPTED_TYPES: Record<string, string[]> = {
	"application/pdf": [".pdf"],
	"application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
	"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
	"text/csv": [".csv"],
	"text/plain": [".txt", ".md"],
	"audio/mpeg": [".mp3"],
	"audio/wav": [".wav"],
	"video/mp4": [".mp4"],
	"image/png": [".png"],
	"image/jpeg": [".jpg", ".jpeg"],
	"image/svg+xml": [".svg"],
};

type UploadState = "idle" | "uploading" | "done" | "error";

interface UploadResult {
	name: string;
	state: UploadState;
	error?: string;
}

async function uploadFile(file: File): Promise<void> {
	// Step 1: request presigned upload URL
	const intentRes = await fetch("/api/files/upload-intent", {
		method: "POST",
		headers: { "content-type": "application/json" },
		body: JSON.stringify({
			filename: file.name,
			content_type: file.type,
			size_bytes: file.size,
		}),
	});

	if (!intentRes.ok) {
		const err = (await intentRes.json().catch(() => ({}))) as { code?: string };
		throw new Error(err.code ?? "UPLOAD_INTENT_FAILED");
	}

	const { upload_url } = (await intentRes.json()) as { upload_url: string };

	// Step 2: PUT directly to object store via presigned URL
	const uploadRes = await fetch(upload_url, {
		method: "PUT",
		headers: { "content-type": file.type },
		body: file,
	});

	if (!uploadRes.ok) {
		throw new Error("UPLOAD_FAILED");
	}
}

interface UploadDropzoneProps {
	onUploaded?: (filename: string) => void;
}

export function UploadDropzone({ onUploaded }: UploadDropzoneProps) {
	const [results, setResults] = useState<UploadResult[]>([]);

	const onDrop = useCallback(
		async (accepted: File[]) => {
			const initial: UploadResult[] = accepted.map((f) => ({
				name: f.name,
				state: "uploading",
			}));
			setResults((prev) => [...initial, ...prev]);

			await Promise.allSettled(
				accepted.map(async (file) => {
					try {
						await uploadFile(file);
						setResults((prev) =>
							prev.map((r) => (r.name === file.name ? { ...r, state: "done" } : r)),
						);
						onUploaded?.(file.name);
					} catch (err) {
						setResults((prev) =>
							prev.map((r) =>
								r.name === file.name ? { ...r, state: "error", error: getErrorMessage(err) } : r,
							),
						);
					}
				}),
			);
		},
		[onUploaded],
	);

	const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
		onDrop,
		accept: ACCEPTED_TYPES,
		maxSize: 5 * 1024 * 1024, // 5MB — use uppy+tus for larger (v1.5)
		multiple: true,
	});

	return (
		<div className="flex flex-col gap-3">
			<div
				{...getRootProps()}
				className={cn(
					"flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 cursor-pointer transition-colors",
					isDragActive
						? "border-emerald-500 bg-emerald-500/5"
						: "border-border hover:border-muted-foreground/50 hover:bg-accent/30",
				)}
			>
				<input {...getInputProps()} />
				<UploadCloud
					className={cn(
						"h-8 w-8 transition-colors",
						isDragActive ? "text-emerald-500" : "text-muted-foreground/50",
					)}
				/>
				<div className="text-center">
					<p className="text-sm font-medium">
						{isDragActive ? "Drop files here" : "Drag & drop or click to upload"}
					</p>
					<p className="text-xs text-muted-foreground/60 mt-1">
						PDF, DOCX, XLSX, CSV, MP3, MP4, PNG, JPG — max 5 MB
					</p>
					<p className="text-[10px] text-muted-foreground/40 mt-0.5 font-mono">
						{">"} 5 MB: uppy + tus (v1.5)
					</p>
				</div>
			</div>

			{fileRejections.length > 0 && (
				<p className="text-xs text-destructive flex items-center gap-1">
					<AlertTriangle className="h-3.5 w-3.5 shrink-0" />
					{fileRejections[0]?.errors[0]?.message ?? "File rejected"}
				</p>
			)}

			{results.length > 0 && (
				<div className="flex flex-col divide-y divide-border/50">
					{results.map((r) => (
						<div key={r.name} className="flex items-center gap-2 py-1.5">
							{r.state === "uploading" && (
								<Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground" />
							)}
							{r.state === "done" && (
								<CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
							)}
							{r.state === "error" && (
								<AlertTriangle className="h-3.5 w-3.5 shrink-0 text-destructive" />
							)}
							<span className="text-xs truncate flex-1 font-medium">{r.name}</span>
							{r.error && (
								<span className="text-[10px] font-mono text-destructive shrink-0">{r.error}</span>
							)}
						</div>
					))}
				</div>
			)}
		</div>
	);
}
