"use client";

import type { UploadQueueItem } from "@matrix/lib/hooks/useUploadQueue";
import { CheckCircle2, Crop, FileIcon, RotateCcw, X } from "lucide-react";
import { useState } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ImageEditor } from "./ImageEditor";

interface Props {
	items: UploadQueueItem[];
	onRemove: (id: string) => void;
	onRetry: (id: string) => void;
	onReplaceFile?: (id: string, newFile: File) => void;
}

function isEditableImage(file: File): boolean {
	return file.type.startsWith("image/") && file.type !== "image/gif";
}

/**
 * Kleine Leiste unterhalb des Composers die die Upload-Queue anzeigt.
 *
 * Pro Item:
 *  - Thumbnail (Bild/Video) oder Datei-Icon
 *  - Dateiname + Status-Text
 *  - Progress-Bar wenn uploading
 *  - Edit-Button (N4) bei Bildern (!= gif) vor Upload
 *  - Retry-Button bei error, X-Button sonst
 */
export function UploadQueueBar({ items, onRemove, onRetry, onReplaceFile }: Props) {
	const [editingId, setEditingId] = useState<string | null>(null);
	if (items.length === 0) return null;

	const editingItem = editingId ? items.find((it) => it.id === editingId) : null;
	const canEdit = (item: UploadQueueItem) =>
		onReplaceFile &&
		(item.status === "pending" || item.status === "error") &&
		isEditableImage(item.file);

	return (
		<div className="flex flex-col gap-1 px-3 py-2 border-t">
			{items.map((item) => (
				<div
					key={item.id}
					className="flex items-center gap-2 rounded-md bg-muted/30 px-2 py-1.5 text-sm"
				>
					<div className="h-10 w-10 shrink-0 overflow-hidden rounded bg-background">
						{item.previewUrl ? (
							// biome-ignore lint/performance/noImgElement: local object URL preview
							<img
								src={item.previewUrl}
								alt={item.file.name}
								className="h-full w-full object-cover"
							/>
						) : (
							<div className="flex h-full w-full items-center justify-center">
								<FileIcon className="h-5 w-5 text-muted-foreground" />
							</div>
						)}
					</div>

					<div className="min-w-0 flex-1">
						<div className="truncate text-xs font-medium">{item.file.name}</div>
						<div className="text-[11px] text-muted-foreground">
							{item.status === "pending" && "Wartet…"}
							{item.status === "uploading" && `Upload… ${item.progress}%`}
							{item.status === "done" && (
								<span className="inline-flex items-center gap-1 text-emerald-600">
									<CheckCircle2 className="h-3 w-3" /> Fertig
								</span>
							)}
							{item.status === "error" && (
								<span className="text-destructive">Fehler: {item.error ?? "unbekannt"}</span>
							)}
						</div>
						{item.status === "uploading" && (
							<div className="mt-1 h-1 w-full overflow-hidden rounded bg-muted">
								<div
									className="h-full bg-primary transition-all"
									style={{ width: `${item.progress}%` }}
								/>
							</div>
						)}
					</div>

					<div className="flex shrink-0 gap-1">
						{canEdit(item) && (
							<button
								type="button"
								onClick={() => setEditingId(item.id)}
								className="rounded p-1 hover:bg-muted"
								title="Bearbeiten"
								aria-label="Bild bearbeiten"
							>
								<Crop className="h-3.5 w-3.5" />
							</button>
						)}
						{onReplaceFile &&
							item.file.type === "image/gif" &&
							(item.status === "pending" || item.status === "error") && (
								<Tooltip>
									<TooltipTrigger asChild>
										<button
											type="button"
											className="rounded p-1 opacity-40 cursor-not-allowed"
											disabled
											aria-label="GIF kann nicht bearbeitet werden"
										>
											<Crop className="h-3.5 w-3.5" />
										</button>
									</TooltipTrigger>
									<TooltipContent>
										Animated GIFs können nicht bearbeitet werden (Animation würde verloren gehen).
									</TooltipContent>
								</Tooltip>
							)}
						{item.status === "error" && (
							<button
								type="button"
								onClick={() => onRetry(item.id)}
								className="rounded p-1 hover:bg-muted"
								title="Erneut versuchen"
							>
								<RotateCcw className="h-3.5 w-3.5" />
							</button>
						)}
						<button
							type="button"
							onClick={() => onRemove(item.id)}
							className="rounded p-1 hover:bg-muted"
							title="Entfernen"
						>
							<X className="h-3.5 w-3.5" />
						</button>
					</div>
				</div>
			))}

			{editingItem && onReplaceFile && (
				<ImageEditor
					open={true}
					onOpenChange={(open) => {
						if (!open) setEditingId(null);
					}}
					file={editingItem.file}
					onSave={(edited) => {
						onReplaceFile(editingItem.id, edited);
						setEditingId(null);
					}}
				/>
			)}
		</div>
	);
}
