"use client";

// DW6 — DocumentViewer: @react-pdf-viewer/core v3.12 + default-layout plugin
// Includes: toolbar, search, thumbnail sidebar
// Worker: CDN (avoids Turbopack/webpack worker-loader complexity with pdfjs-dist 3.x)
// v1.5: RAG Chunk-Overlay plugin (DW22), AI Sidebar Stream (DW23)

import { type LoadError, Viewer, Worker } from "@react-pdf-viewer/core";
import { defaultLayoutPlugin } from "@react-pdf-viewer/default-layout";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, FileText, Loader2 } from "lucide-react";
import { useState } from "react";
import { getErrorMessage } from "@/lib/utils";
import { FileSearch } from "./FileSearch";

import "@react-pdf-viewer/core/lib/styles/index.css";
import "@react-pdf-viewer/default-layout/lib/styles/index.css";

const PDFJS_VERSION = "3.11.174";
const WORKER_URL = `https://unpkg.com/pdfjs-dist@${PDFJS_VERSION}/build/pdf.worker.min.js`;

interface FileRecord {
	id: string;
	name: string;
	type: string;
	status: string;
	created_at: string;
}

interface FilesListResponse {
	total_documents: number;
	indexing_pending: number;
	indexing_failed: number;
	recent_uploads: FileRecord[];
}

async function fetchPresignedUrl(id: string): Promise<string> {
	const res = await fetch(`/api/files/${encodeURIComponent(id)}/url`, { cache: "no-store" });
	if (!res.ok) {
		const err = (await res.json().catch(() => ({}))) as { code?: string };
		throw new Error(err.code ?? "NO_DOCUMENT_INDEX");
	}
	const data = (await res.json()) as { url: string };
	return data.url;
}

function renderPdfError(err: LoadError) {
	return (
		<div className="flex flex-1 flex-col items-center justify-center gap-2 text-destructive">
			<AlertTriangle className="h-6 w-6" />
			<p className="text-sm font-medium">Failed to load PDF</p>
			<p className="text-xs font-mono">{err.message ?? "PDF_LOAD_FAILED"}</p>
		</div>
	);
}

export function DocumentViewer() {
	const defaultLayout = defaultLayoutPlugin();
	const [selectedFile, setSelectedFile] = useState<FileRecord | null>(null);
	const [pdfError, setPdfError] = useState<string | null>(null);

	const {
		data: filesList,
		isLoading: listLoading,
		isError: listError,
		error: listErr,
	} = useQuery<FilesListResponse, Error>({
		queryKey: ["files-list"],
		queryFn: async () => {
			const res = await fetch("/api/files", { cache: "no-store" });
			if (!res.ok) {
				const e = (await res.json().catch(() => ({}))) as { code?: string };
				throw new Error(e.code ?? "STORAGE_UNAVAILABLE");
			}
			return res.json() as Promise<FilesListResponse>;
		},
		staleTime: 30_000,
		retry: 1,
	});

	const { data: pdfUrl, isLoading: urlLoading } = useQuery<string, Error>({
		queryKey: ["file-url", selectedFile?.id],
		queryFn: () => fetchPresignedUrl(selectedFile!.id),
		enabled: !!selectedFile,
		staleTime: 10 * 60 * 1000, // 10 min — presigned URL TTL is 15 min
		retry: false,
	});

	const documents = filesList?.recent_uploads ?? [];

	return (
		<div className="flex h-full min-h-0">
			{/* Left: file list + search */}
			<div className="w-64 shrink-0 flex flex-col gap-3 border-r border-border p-3 overflow-y-auto">
				<p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
					Documents
				</p>

				{listLoading && (
					<div className="flex items-center gap-2 text-muted-foreground text-xs">
						<Loader2 className="h-3.5 w-3.5 animate-spin" />
						Loading…
					</div>
				)}

				{listError && (
					<div className="flex items-center gap-1.5 text-destructive text-xs">
						<AlertTriangle className="h-3.5 w-3.5 shrink-0" />
						<span className="font-mono">{getErrorMessage(listErr)}</span>
					</div>
				)}

				{!listLoading && !listError && (
					<FileSearch
						files={documents}
						onSelect={(f) => {
							setSelectedFile(f);
							setPdfError(null);
						}}
					/>
				)}
			</div>

			{/* Right: PDF viewer */}
			<div className="flex flex-1 flex-col min-h-0 min-w-0">
				{!selectedFile ? (
					<div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
						<FileText className="h-8 w-8 text-muted-foreground/30" />
						<p className="text-sm">Select a document to view</p>
					</div>
				) : urlLoading ? (
					<div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground">
						<Loader2 className="h-5 w-5 animate-spin" />
						<span className="text-sm">Loading document…</span>
					</div>
				) : pdfError ? (
					<div className="flex flex-1 flex-col items-center justify-center gap-2 text-destructive">
						<AlertTriangle className="h-6 w-6" />
						<p className="text-sm font-medium">Failed to load PDF</p>
						<p className="text-xs font-mono">{pdfError}</p>
					</div>
				) : pdfUrl ? (
					<div className="flex-1 min-h-0 overflow-hidden">
						<Worker workerUrl={WORKER_URL}>
							<Viewer fileUrl={pdfUrl} plugins={[defaultLayout]} renderError={renderPdfError} />
						</Worker>
					</div>
				) : null}
			</div>
		</div>
	);
}
