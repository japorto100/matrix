"use client";

import type { ResolvedMessage } from "@matrix/lib/types";
import { formatFileSize } from "@matrix/lib/utils";
import { Download, File, FileText, Film, LayoutGrid, Music } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

function fileIcon(mimeType?: string) {
	if (!mimeType) return <File className="h-5 w-5" />;
	if (mimeType.startsWith("video/")) return <Film className="h-5 w-5" />;
	if (mimeType.startsWith("audio/")) return <Music className="h-5 w-5" />;
	if (mimeType.includes("pdf") || mimeType.includes("text"))
		return <FileText className="h-5 w-5" />;
	return <File className="h-5 w-5" />;
}

function GenericFileContent({ message }: { message: ResolvedMessage }) {
	return (
		<a
			href={message.url ?? "#"}
			target="_blank"
			rel="noopener noreferrer"
			download={message.fileName}
			className="flex items-center gap-3 bg-muted/50 rounded-xl px-3 py-2.5 hover:bg-muted transition-colors no-underline max-w-[280px]"
		>
			<div className="text-primary shrink-0">{fileIcon(message.mimeType)}</div>
			<div className="flex-1 min-w-0">
				<p className="text-xs font-medium truncate">{message.fileName ?? message.body}</p>
				{message.fileSize !== undefined && (
					<p className="text-[10px] text-muted-foreground">{formatFileSize(message.fileSize)}</p>
				)}
			</div>
			<Download className="h-4 w-4 text-muted-foreground shrink-0" />
		</a>
	);
}

function DocxContent({ message }: { message: ResolvedMessage }) {
	const [showPreview, setShowPreview] = useState(false);
	const containerRef = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (!showPreview || !message.url || !containerRef.current) return;
		let cancelled = false;
		(async () => {
			try {
				const { renderAsync } = await import("docx-preview");
				const res = await fetch(message.url!);
				const blob = await res.blob();
				if (cancelled || !containerRef.current) return;
				containerRef.current.innerHTML = "";
				await renderAsync(blob, containerRef.current, undefined, { className: "docx-preview" });
			} catch (err) {
				console.error("[DocxContent] render failed:", err);
				if (containerRef.current)
					containerRef.current.innerHTML =
						"<p class='p-4 text-sm text-muted-foreground'>Vorschau nicht verfügbar</p>";
			}
		})();
		return () => {
			cancelled = true;
		};
	}, [showPreview, message.url]);

	return (
		<>
			<button
				type="button"
				onClick={() => setShowPreview(true)}
				className="flex items-center gap-3 bg-muted/50 rounded-xl px-3 py-2.5 hover:bg-muted transition-colors max-w-[280px] border-0 cursor-pointer text-left"
			>
				<FileText className="h-5 w-5 text-blue-500 shrink-0" />
				<div className="flex-1 min-w-0">
					<p className="text-xs font-medium truncate">{message.fileName ?? message.body}</p>
					{message.fileSize !== undefined && (
						<p className="text-[10px] text-muted-foreground">{formatFileSize(message.fileSize)}</p>
					)}
				</div>
			</button>
			{showPreview && (
				<Dialog open={showPreview} onOpenChange={setShowPreview}>
					<DialogContent
						className="max-w-[80vw] max-h-[85vh] p-0 border-none overflow-hidden"
						aria-describedby={undefined}
					>
						<DialogTitle className="sr-only">{message.fileName ?? "Dokument"}</DialogTitle>
						<div ref={containerRef} className="w-full h-[80vh] overflow-auto bg-white p-4" />
					</DialogContent>
				</Dialog>
			)}
		</>
	);
}

function XlsxContent({ message }: { message: ResolvedMessage }) {
	const [showPreview, setShowPreview] = useState(false);
	const [tableHtml, setTableHtml] = useState<string>("");
	useEffect(() => {
		if (!showPreview || !message.url) return;
		let cancelled = false;
		(async () => {
			try {
				const XLSX = await import("xlsx");
				const res = await fetch(message.url!);
				const buf = await res.arrayBuffer();
				if (cancelled) return;
				const wb = XLSX.read(buf, { type: "array" });
				const sheetName = wb.SheetNames[0];
				const ws = sheetName ? wb.Sheets[sheetName] : undefined;
				if (ws) setTableHtml(XLSX.utils.sheet_to_html(ws));
			} catch (err) {
				console.error("[XlsxContent] render failed:", err);
				setTableHtml("<p class='p-4 text-sm'>Vorschau nicht verfügbar</p>");
			}
		})();
		return () => {
			cancelled = true;
		};
	}, [showPreview, message.url]);

	return (
		<>
			<button
				type="button"
				onClick={() => setShowPreview(true)}
				className="flex items-center gap-3 bg-muted/50 rounded-xl px-3 py-2.5 hover:bg-muted transition-colors max-w-[280px] border-0 cursor-pointer text-left"
			>
				<LayoutGrid className="h-5 w-5 text-emerald-500 shrink-0" />
				<div className="flex-1 min-w-0">
					<p className="text-xs font-medium truncate">{message.fileName ?? message.body}</p>
					{message.fileSize !== undefined && (
						<p className="text-[10px] text-muted-foreground">{formatFileSize(message.fileSize)}</p>
					)}
				</div>
			</button>
			{showPreview && (
				<Dialog open={showPreview} onOpenChange={setShowPreview}>
					<DialogContent
						className="max-w-[80vw] max-h-[85vh] p-0 border-none overflow-hidden"
						aria-describedby={undefined}
					>
						<DialogTitle className="sr-only">{message.fileName ?? "Tabelle"}</DialogTitle>
						<div
							className="w-full h-[80vh] overflow-auto bg-white p-4 text-black [&_table]:w-full [&_table]:border-collapse [&_td]:border [&_td]:border-gray-300 [&_td]:px-2 [&_td]:py-1 [&_td]:text-xs [&_th]:border [&_th]:border-gray-300 [&_th]:px-2 [&_th]:py-1 [&_th]:text-xs [&_th]:bg-gray-100 [&_th]:font-semibold"
							// biome-ignore lint/security/noDangerouslySetInnerHtml: SheetJS HTML
							dangerouslySetInnerHTML={{ __html: tableHtml }}
						/>
					</DialogContent>
				</Dialog>
			)}
		</>
	);
}

function PdfContent({ message }: { message: ResolvedMessage }) {
	const [showPreview, setShowPreview] = useState(false);
	if (!message.url) return <GenericFileContent message={message} />;
	return (
		<>
			<button
				type="button"
				onClick={() => setShowPreview(true)}
				className="flex items-center gap-3 bg-muted/50 rounded-xl px-3 py-2.5 hover:bg-muted transition-colors max-w-[280px] border-0 cursor-pointer text-left"
			>
				<FileText className="h-5 w-5 text-red-500 shrink-0" />
				<div className="flex-1 min-w-0">
					<p className="text-xs font-medium truncate">{message.fileName ?? message.body}</p>
					{message.fileSize !== undefined && (
						<p className="text-[10px] text-muted-foreground">{formatFileSize(message.fileSize)}</p>
					)}
				</div>
			</button>
			{showPreview && (
				<Dialog open={showPreview} onOpenChange={setShowPreview}>
					<DialogContent
						className="max-w-[80vw] max-h-[85vh] p-0 border-none overflow-hidden"
						aria-describedby={undefined}
					>
						<DialogTitle className="sr-only">{message.fileName ?? "PDF"}</DialogTitle>
						<iframe
							src={message.url}
							title={message.fileName ?? "PDF"}
							className="w-full h-[80vh] border-0"
						/>
					</DialogContent>
				</Dialog>
			)}
		</>
	);
}

export function FileContent({ message }: { message: ResolvedMessage }) {
	const mime = message.mimeType ?? "";
	const ext = (message.fileName ?? "").split(".").pop()?.toLowerCase();
	if (mime === "application/pdf") return <PdfContent message={message} />;
	if (
		mime === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
		ext === "docx"
	)
		return <DocxContent message={message} />;
	if (
		mime === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
		ext === "xlsx" ||
		ext === "xls" ||
		ext === "csv"
	)
		return <XlsxContent message={message} />;
	return <GenericFileContent message={message} />;
}
