"use client";

// AC52+exec-12: AttachmentPreviewStrip — thumbnails for images, icons for data/code files

import { FileCode, FileSpreadsheet, FileText, X } from "lucide-react";
import type { StagedAttachment } from "../hooks/useAttachments";

interface AttachmentPreviewStripProps {
	attachments: StagedAttachment[];
	onRemove: (id: string) => void;
	onPreview: (attachment: StagedAttachment) => void;
}

function isImageType(mime: string): boolean {
	return mime.startsWith("image/");
}

function FileIcon({ mime, name }: { mime: string; name: string }) {
	const ext = name.split(".").pop()?.toLowerCase() ?? "";
	if (
		mime === "text/csv" ||
		ext === "xlsx" ||
		ext === "xls" ||
		mime.includes("spreadsheet") ||
		mime.includes("ms-excel")
	) {
		return <FileSpreadsheet className="h-6 w-6 text-emerald-500" />;
	}
	if (
		ext === "py" ||
		ext === "js" ||
		ext === "ts" ||
		mime.includes("python") ||
		mime.includes("javascript")
	) {
		return <FileCode className="h-6 w-6 text-blue-500" />;
	}
	return <FileText className="h-6 w-6 text-muted-foreground" />;
}

export function AttachmentPreviewStrip({
	attachments,
	onRemove,
	onPreview,
}: AttachmentPreviewStripProps) {
	if (attachments.length === 0) return null;

	return (
		<div className="flex gap-2 px-1 pb-1 overflow-x-auto shrink-0 scrollbar-thin">
			{attachments.map((att) => (
				<div key={att.id} className="relative shrink-0 group">
					<button
						type="button"
						onClick={() => onPreview(att)}
						className="flex items-center justify-center h-14 w-14 rounded border border-border overflow-hidden hover:opacity-80 transition-opacity"
						title={att.name}
					>
						{isImageType(att.file.type) ? (
							/* biome-ignore lint/performance/noImgElement: previewUrl is a blob: URL — Next.js <Image> cannot optimize blob: URLs */
							<img src={att.previewUrl} alt={att.name} className="h-full w-full object-cover" />
						) : (
							<div className="flex flex-col items-center gap-0.5 px-1">
								<FileIcon mime={att.file.type} name={att.name} />
								<span className="text-[8px] text-muted-foreground truncate max-w-[50px]">
									{att.name.split(".").pop()}
								</span>
							</div>
						)}
					</button>
					<button
						type="button"
						onClick={() => onRemove(att.id)}
						className="absolute -top-1.5 -right-1.5 h-4 w-4 rounded-full bg-background border border-border flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive hover:text-destructive-foreground hover:border-destructive"
						title="Remove"
					>
						<X className="h-2.5 w-2.5" />
					</button>
				</div>
			))}
		</div>
	);
}
