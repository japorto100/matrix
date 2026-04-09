"use client";

// DW6 — DocumentViewer: react-pdf v10 + supermemory pattern
// (originally @react-pdf-viewer/core v3.12 from control/files_surface, migrated
//  on 2026-04-07 to react-pdf v10 to align with nextjs-chat + supermemory).
//
// Worker source: pdfjs-dist bundled with react-pdf (no CDN dependency).
// v1.5: RAG Chunk-Overlay plugin (DW22), AI Sidebar Stream (DW23)

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, FileText, Loader2, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/lib/utils";
import { FileSearch } from "./FileSearch";
import { ReindexConfirmDialog } from "./ReindexConfirmDialog";

// Configure PDF.js worker — use local package, not CDN
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
	"pdfjs-dist/build/pdf.worker.min.mjs",
	import.meta.url,
).toString();

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
	const res = await fetch(`/api/files/${encodeURIComponent(id)}/url`, {
		cache: "no-store",
	});
	if (!res.ok) {
		const err = (await res.json().catch(() => ({}))) as { code?: string };
		throw new Error(err.code ?? "NO_DOCUMENT_INDEX");
	}
	const data = (await res.json()) as { url: string };
	return data.url;
}

export function DocumentViewer() {
	const [selectedFile, setSelectedFile] = useState<FileRecord | null>(null);
	const [numPages, setNumPages] = useState<number | null>(null);
	const [pdfError, setPdfError] = useState<string | null>(null);
	const [reindexOpen, setReindexOpen] = useState(false);

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

	function onDocumentLoadSuccess({ numPages: n }: { numPages: number }) {
		setNumPages(n);
		setPdfError(null);
	}

	function onDocumentLoadError(err: Error) {
		setPdfError(err.message || "Failed to load PDF");
	}

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
							setNumPages(null);
						}}
					/>
				)}
			</div>

			{/* Right: PDF viewer (react-pdf v10 — supermemory pattern) */}
			<div className="flex flex-1 flex-col min-h-0 min-w-0">
				{selectedFile && (
					<div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-border bg-card/30 shrink-0">
						<div className="flex items-center gap-2 min-w-0">
							<FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
							<span className="text-xs font-medium truncate">{selectedFile.name}</span>
							<span className="text-[10px] font-mono uppercase text-muted-foreground shrink-0">
								{selectedFile.type}
							</span>
						</div>
						<Button
							variant="outline"
							size="sm"
							className="h-7 gap-1.5 text-xs shrink-0"
							onClick={() => setReindexOpen(true)}
						>
							<RefreshCw className="h-3 w-3" />
							Reindex
						</Button>
					</div>
				)}
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
					<div className="flex-1 overflow-auto w-full bg-card/20">
						<Document
							file={pdfUrl}
							onLoadSuccess={onDocumentLoadSuccess}
							onLoadError={onDocumentLoadError}
							loading={
								<div className="flex items-center justify-center h-32 text-muted-foreground">
									<Loader2 className="h-5 w-5 animate-spin" />
								</div>
							}
							className="w-full"
						>
							{numPages && (
								<div className="flex flex-col items-center gap-4 py-4 w-full">
									{Array.from({ length: numPages }, (_, index) => (
										<Page
											key={`page_${index + 1}`}
											pageNumber={index + 1}
											renderTextLayer
											renderAnnotationLayer
											className="shadow-lg"
											width={760}
										/>
									))}
								</div>
							)}
						</Document>
					</div>
				) : null}
			</div>

			{selectedFile && (
				<ReindexConfirmDialog
					open={reindexOpen}
					fileId={selectedFile.id}
					fileName={selectedFile.name}
					onClose={() => setReindexOpen(false)}
					onSuccess={() => toast.success(`Reindex queued for ${selectedFile.name}`)}
				/>
			)}
		</div>
	);
}
