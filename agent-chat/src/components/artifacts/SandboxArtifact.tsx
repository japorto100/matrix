"use client";

/**
 * SandboxArtifact — exec-13 Phase 6.3
 *
 * Rendert OpenSandbox Execution Results (Charts, Tables, Files) inline im Chat.
 * Der sandbox_execute Tool gibt stdout + files (base64 Charts) zurück.
 * Diese Component rendert die Ergebnisse als visuelle Artifacts.
 */

import { FileImage, FileText, Terminal } from "lucide-react";

export interface SandboxArtifactProps {
	/** stdout vom Sandbox-Execution */
	stdout?: string;
	/** stderr vom Sandbox-Execution */
	stderr?: string;
	/** Dateien aus der Sandbox (Charts, CSVs, etc.) */
	files?: Array<{
		name: string;
		content_b64: string;
		mime_type?: string;
	}>;
	/** Execution-Zeit in ms */
	execution_time_ms?: number;
	/** Sprache die ausgeführt wurde */
	language?: string;
}

export function SandboxArtifact({
	stdout,
	stderr,
	files,
	execution_time_ms,
	language,
}: SandboxArtifactProps) {
	const hasOutput = stdout || stderr;
	const hasFiles = files && files.length > 0;

	if (!hasOutput && !hasFiles) {
		return (
			<div className="text-[10px] text-muted-foreground italic">
				Sandbox-Execution abgeschlossen (keine Ausgabe)
			</div>
		);
	}

	return (
		<div className="my-2 space-y-2">
			{/* Header */}
			<div className="flex items-center gap-2 text-[10px] text-muted-foreground">
				<Terminal className="h-3 w-3" />
				<span>
					Sandbox {language ?? "code"} —{" "}
					{execution_time_ms != null
						? `${(execution_time_ms / 1000).toFixed(1)}s`
						: "completed"}
				</span>
			</div>

			{/* stdout */}
			{stdout && (
				<pre className="rounded-md bg-muted/40 border border-border/30 px-3 py-2 text-[11px] leading-relaxed max-h-60 overflow-auto whitespace-pre-wrap">
					{stdout}
				</pre>
			)}

			{/* stderr (nur bei Fehler) */}
			{stderr && (
				<pre className="rounded-md bg-red-950/30 border border-red-800/30 px-3 py-2 text-[11px] leading-relaxed max-h-40 overflow-auto text-red-300 whitespace-pre-wrap">
					{stderr}
				</pre>
			)}

			{/* Files (Charts als Bilder, Rest als Downloads) */}
			{hasFiles && (
				<div className="space-y-2">
					{files.map((file) => {
						const isImage =
							file.mime_type?.startsWith("image/") ||
							/\.(png|jpg|jpeg|gif|svg|webp)$/i.test(file.name);

						if (isImage) {
							return (
								<div key={file.name} className="space-y-1">
									<div className="flex items-center gap-1 text-[10px] text-muted-foreground">
										<FileImage className="h-3 w-3" />
										<span>{file.name}</span>
									</div>
									{/* biome-ignore lint/performance/noImgElement: base64 data URI — Next.js Image cannot optimize */}
									<img
										src={`data:${file.mime_type ?? "image/png"};base64,${file.content_b64}`}
										alt={file.name}
										className="rounded-md border border-border/30 max-w-full max-h-80"
									/>
								</div>
							);
						}

						return (
							<a
								key={file.name}
								href={`data:${file.mime_type ?? "application/octet-stream"};base64,${file.content_b64}`}
								download={file.name}
								className="flex items-center gap-1.5 text-[11px] text-primary hover:underline"
							>
								<FileText className="h-3 w-3" />
								<span>{file.name}</span>
							</a>
						);
					})}
				</div>
			)}
		</div>
	);
}
