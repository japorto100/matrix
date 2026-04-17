"use client";

// AC55: ImagePreviewModal — fullscreen lightbox for image attachment preview

import { X, ZoomIn, ZoomOut } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { StagedAttachment } from "../hooks/useAttachments";

interface ImagePreviewModalProps {
	attachment: StagedAttachment | null;
	onClose: () => void;
}

export function ImagePreviewModal({ attachment, onClose }: ImagePreviewModalProps) {
	const [scale, setScale] = useState(1);

	useEffect(() => {
		if (attachment) setScale(1);
	}, [attachment]);

	const handleKey = useCallback(
		(e: KeyboardEvent) => {
			if (e.key === "Escape") onClose();
		},
		[onClose],
	);

	useEffect(() => {
		if (!attachment) return;
		window.addEventListener("keydown", handleKey);
		return () => window.removeEventListener("keydown", handleKey);
	}, [attachment, handleKey]);

	if (!attachment) return null;

	return (
		<div
			className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-sm"
			onClick={onClose}
			onKeyDown={(e) => {
				if (e.key === "Escape") onClose();
			}}
		>
			<div
				className="relative max-w-[90vw] max-h-[90vh]"
				onClick={(e) => e.stopPropagation()}
				onKeyDown={(e) => e.stopPropagation()}
			>
				{/* biome-ignore lint/performance/noImgElement: blob: URL + CSS zoom transform — Next.js <Image> cannot optimize blob: URLs and wraps in div which breaks scale() */}
				<img
					src={attachment.previewUrl}
					alt={attachment.name}
					style={{ transform: `scale(${scale})`, transition: "transform 0.15s ease" }}
					className="max-w-[90vw] max-h-[85vh] object-contain rounded-lg shadow-2xl"
				/>

				<div className="absolute top-2 right-2 flex gap-1">
					<button
						type="button"
						onClick={() => setScale((s) => Math.min(s + 0.25, 3))}
						className="h-8 w-8 rounded bg-black/60 text-white flex items-center justify-center hover:bg-black/80 transition-colors"
						title="Zoom in"
					>
						<ZoomIn className="h-4 w-4" />
					</button>
					<button
						type="button"
						onClick={() => setScale((s) => Math.max(s - 0.25, 0.25))}
						className="h-8 w-8 rounded bg-black/60 text-white flex items-center justify-center hover:bg-black/80 transition-colors"
						title="Zoom out"
					>
						<ZoomOut className="h-4 w-4" />
					</button>
					<button
						type="button"
						onClick={onClose}
						className="h-8 w-8 rounded bg-black/60 text-white flex items-center justify-center hover:bg-black/80 transition-colors"
						title="Close (Esc)"
					>
						<X className="h-4 w-4" />
					</button>
				</div>

				<div className="absolute bottom-2 left-0 right-0 text-center pointer-events-none">
					<span className="text-[11px] text-white/60 bg-black/40 rounded px-2 py-0.5">
						{attachment.name}
					</span>
				</div>
			</div>
		</div>
	);
}
