"use client";

// AC52: AttachmentPreviewStrip — horizontal scroll strip of staged image thumbnails

import { X } from "lucide-react";
import type { StagedAttachment } from "../hooks/useAttachments";

interface AttachmentPreviewStripProps {
	attachments: StagedAttachment[];
	onRemove: (id: string) => void;
	onPreview: (attachment: StagedAttachment) => void;
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
						className="block h-14 w-14 rounded border border-border overflow-hidden hover:opacity-80 transition-opacity"
						title={att.name}
					>
						{/* biome-ignore lint/performance/noImgElement: previewUrl is a blob: URL from URL.createObjectURL — Next.js <Image> cannot optimize blob: URLs */}
						<img src={att.previewUrl} alt={att.name} className="h-full w-full object-cover" />
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
