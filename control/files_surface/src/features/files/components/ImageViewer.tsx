"use client";

// DW10 — ImageViewer: next/image + lightbox zoom + SVG annotation layer placeholder
// v1: display + zoom; v1.5: AI Vision overlay (Claude Vision → pattern annotations)

import { X, ZoomIn } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface ImageAnnotation {
	x: number; // 0-100 (percentage)
	y: number;
	label: string;
	confidence?: number;
}

interface ImageViewerProps {
	src: string;
	alt?: string;
	annotations?: ImageAnnotation[]; // v1.5: populated by Claude Vision
	className?: string;
}

export function ImageViewer({
	src,
	alt = "File image",
	annotations = [],
	className,
}: ImageViewerProps) {
	const [lightbox, setLightbox] = useState(false);

	return (
		<>
			{/* Thumbnail + zoom trigger */}
			<div
				className={cn(
					"relative group overflow-hidden rounded-lg border border-border cursor-zoom-in",
					className,
				)}
				onClick={() => setLightbox(true)}
			>
				<div className="relative w-full aspect-video bg-muted/30">
					<Image
						src={src}
						alt={alt}
						fill
						sizes="(max-width: 768px) 100vw, 50vw"
						className="object-contain"
						unoptimized={src.startsWith("blob:")}
					/>
				</div>

				{/* SVG annotation layer (v1.5 — rendered over image) */}
				{annotations.length > 0 && (
					<svg
						className="absolute inset-0 w-full h-full pointer-events-none"
						viewBox="0 0 100 100"
						preserveAspectRatio="none"
					>
						{annotations.map((ann) => (
							<g key={`${ann.x}-${ann.y}-${ann.label}`}>
								<circle cx={ann.x} cy={ann.y} r="1.5" fill="rgba(16,185,129,0.8)" />
								<text
									x={ann.x + 2}
									y={ann.y - 1}
									fontSize="3"
									fill="rgba(16,185,129,1)"
									fontFamily="monospace"
								>
									{ann.label}
									{ann.confidence !== undefined && ` (${Math.round(ann.confidence * 100)}%)`}
								</text>
							</g>
						))}
					</svg>
				)}

				{/* Zoom hint */}
				<div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20">
					<ZoomIn className="h-6 w-6 text-white drop-shadow" />
				</div>
			</div>

			{/* Lightbox */}
			{lightbox && (
				<div
					className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
					onClick={() => setLightbox(false)}
				>
					<button
						className="absolute top-4 right-4 text-white/70 hover:text-white"
						onClick={() => setLightbox(false)}
					>
						<X className="h-6 w-6" />
					</button>
					<div
						className="relative max-w-5xl max-h-[90vh] w-full"
						onClick={(e) => e.stopPropagation()}
					>
						<div className="relative w-full h-[80vh]">
							<Image
								src={src}
								alt={alt}
								fill
								sizes="100vw"
								className="object-contain"
								unoptimized={src.startsWith("blob:")}
							/>
						</div>
					</div>
				</div>
			)}
		</>
	);
}
