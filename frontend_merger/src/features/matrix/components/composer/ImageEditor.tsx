"use client";

import { RotateCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import Cropper, { type Area } from "react-easy-crop";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";

interface Props {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	file: File;
	onSave: (editedFile: File) => void;
}

type AspectMode = "4:3" | "1:1" | "16:9" | "3:4";

const ASPECTS: Record<AspectMode, number> = {
	"4:3": 4 / 3,
	"1:1": 1,
	"16:9": 16 / 9,
	"3:4": 3 / 4,
};

/**
 * N4 — Image-Editor Modal mit Crop + Rotate.
 *
 * Rendert react-easy-crop Cropper. Cancel schliesst unveraendert; Save
 * erzeugt einen neuen File<image/jpeg> aus dem crop+rotation+File und
 * ruft onSave auf.
 *
 * ObjectURL-Lifecycle (Contrarian #5):
 *  - Preview-URL wird bei Mount aus file erzeugt.
 *  - useEffect-Cleanup revoked die URL bei Unmount.
 *  - GIF-Animation ginge durch Canvas-Roundtrip verloren — der Edit-Button
 *    muss im Caller per file.type === 'image/gif' deaktiviert werden.
 */
export function ImageEditor({ open, onOpenChange, file, onSave }: Props) {
	const [imageUrl, setImageUrl] = useState<string>("");
	const [crop, setCrop] = useState({ x: 0, y: 0 });
	const [zoom, setZoom] = useState(1);
	const [rotation, setRotation] = useState(0);
	const [aspect, setAspect] = useState<AspectMode>("4:3");
	const croppedAreaPixelsRef = useRef<Area | null>(null);
	const [saving, setSaving] = useState(false);

	useEffect(() => {
		if (!open) return;
		const url = URL.createObjectURL(file);
		setImageUrl(url);
		setCrop({ x: 0, y: 0 });
		setZoom(1);
		setRotation(0);
		setAspect("4:3");
		croppedAreaPixelsRef.current = null;
		return () => {
			URL.revokeObjectURL(url);
		};
	}, [open, file]);

	const onCropComplete = useCallback((_area: Area, areaPixels: Area) => {
		croppedAreaPixelsRef.current = areaPixels;
	}, []);

	const handleSave = useCallback(async () => {
		if (!croppedAreaPixelsRef.current) {
			onOpenChange(false);
			return;
		}
		setSaving(true);
		try {
			const cropped = await renderCroppedImage(
				imageUrl,
				croppedAreaPixelsRef.current,
				rotation,
				file.name,
				file.type,
			);
			onSave(cropped);
			onOpenChange(false);
		} catch (err) {
			console.error("[ImageEditor] crop failed:", err);
			toast.error("Bild konnte nicht bearbeitet werden.");
		} finally {
			setSaving(false);
		}
	}, [imageUrl, rotation, file, onSave, onOpenChange]);

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-2xl">
				<DialogHeader>
					<DialogTitle>Bild bearbeiten</DialogTitle>
				</DialogHeader>
				<div className="relative w-full h-[400px] bg-black/50 rounded-md overflow-hidden">
					{imageUrl && (
						<Cropper
							image={imageUrl}
							crop={crop}
							zoom={zoom}
							rotation={rotation}
							aspect={ASPECTS[aspect]}
							onCropChange={setCrop}
							onZoomChange={setZoom}
							onRotationChange={setRotation}
							onCropComplete={onCropComplete}
						/>
					)}
				</div>

				<div className="grid grid-cols-2 gap-4 pt-2">
					<div className="space-y-1.5">
						<Label className="text-xs">Seitenverhältnis</Label>
						<Select value={aspect} onValueChange={(v) => setAspect(v as AspectMode)}>
							<SelectTrigger className="h-8 text-xs">
								<SelectValue />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="4:3">4:3 (Standard)</SelectItem>
								<SelectItem value="1:1">1:1 (Quadrat)</SelectItem>
								<SelectItem value="16:9">16:9 (Breitbild)</SelectItem>
								<SelectItem value="3:4">3:4 (Hochformat)</SelectItem>
							</SelectContent>
						</Select>
					</div>

					<div className="space-y-1.5">
						<Label className="text-xs">Zoom: {zoom.toFixed(1)}×</Label>
						<Slider
							min={1}
							max={4}
							step={0.1}
							value={[zoom]}
							onValueChange={(v) => v[0] !== undefined && setZoom(v[0])}
						/>
					</div>

					<div className="col-span-2 flex gap-2">
						<Button
							type="button"
							variant="outline"
							size="sm"
							onClick={() => setRotation((r) => (r - 90) % 360)}
							className="gap-1.5"
						>
							<RotateCw className="h-3.5 w-3.5 -scale-x-100" />
							Links drehen
						</Button>
						<Button
							type="button"
							variant="outline"
							size="sm"
							onClick={() => setRotation((r) => (r + 90) % 360)}
							className="gap-1.5"
						>
							<RotateCw className="h-3.5 w-3.5" />
							Rechts drehen
						</Button>
						<span className="text-xs text-muted-foreground self-center ml-auto">{rotation}°</span>
					</div>
				</div>

				<DialogFooter>
					<Button
						type="button"
						variant="outline"
						onClick={() => onOpenChange(false)}
						disabled={saving}
					>
						Abbrechen
					</Button>
					<Button type="button" onClick={() => void handleSave()} disabled={saving}>
						{saving ? "Speichere…" : "Übernehmen"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}

async function renderCroppedImage(
	imageSrc: string,
	crop: Area,
	rotation: number,
	originalName: string,
	originalMime: string,
): Promise<File> {
	const image = await loadImage(imageSrc);
	const radians = (rotation * Math.PI) / 180;
	const rotatedBox = getRotatedBox(image.width, image.height, radians);

	// Rotate entire image first onto offscreen canvas.
	const rotatedCanvas = document.createElement("canvas");
	rotatedCanvas.width = rotatedBox.width;
	rotatedCanvas.height = rotatedBox.height;
	const rotatedCtx = rotatedCanvas.getContext("2d");
	if (!rotatedCtx) throw new Error("Canvas 2D context nicht verfuegbar");

	rotatedCtx.translate(rotatedBox.width / 2, rotatedBox.height / 2);
	rotatedCtx.rotate(radians);
	rotatedCtx.drawImage(image, -image.width / 2, -image.height / 2);

	// Now extract the crop from the rotated image.
	const output = document.createElement("canvas");
	output.width = Math.max(1, Math.round(crop.width));
	output.height = Math.max(1, Math.round(crop.height));
	const outCtx = output.getContext("2d");
	if (!outCtx) throw new Error("Canvas 2D context nicht verfuegbar");
	outCtx.drawImage(
		rotatedCanvas,
		crop.x,
		crop.y,
		crop.width,
		crop.height,
		0,
		0,
		output.width,
		output.height,
	);

	// Preserve original mime where possible; fall back to JPEG for safety.
	const outputMime = originalMime === "image/png" ? "image/png" : "image/jpeg";
	const blob = await new Promise<Blob | null>((resolve) => {
		output.toBlob(resolve, outputMime, 0.92);
	});
	if (!blob) throw new Error("Blob-Export fehlgeschlagen");

	const baseName = originalName.replace(/\.[^.]+$/, "");
	const ext = outputMime === "image/png" ? "png" : "jpg";
	return new File([blob], `${baseName}-bearbeitet.${ext}`, { type: outputMime });
}

function loadImage(src: string): Promise<HTMLImageElement> {
	return new Promise((resolve, reject) => {
		const img = new Image();
		img.onload = () => resolve(img);
		img.onerror = reject;
		img.src = src;
	});
}

function getRotatedBox(width: number, height: number, radians: number) {
	const abs = Math.abs;
	return {
		width: abs(Math.cos(radians) * width) + abs(Math.sin(radians) * height),
		height: abs(Math.sin(radians) * width) + abs(Math.cos(radians) * height),
	};
}
