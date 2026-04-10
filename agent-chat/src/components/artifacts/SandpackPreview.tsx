"use client";

/**
 * SandpackPreview — exec-13 Phase 6.2
 *
 * Leichtgewichtige Browser-Preview für React/JS Code direkt im Chat.
 * Kein Server nötig — läuft komplett im Browser via CodeSandbox Sandpack.
 * Für LLM-generierten Frontend-Code (Dashboards, Charts, Widgets).
 */

import {
	SandpackProvider,
	SandpackPreview as SandpackPreviewPane,
	SandpackCodeEditor,
} from "@codesandbox/sandpack-react";
import { Code, Eye } from "lucide-react";
import { useState } from "react";

export interface SandpackPreviewProps {
	/** Dateiname → Code mapping. Mindestens "/App.js" oder "/App.tsx" */
	files: Record<string, string>;
	/** Sandpack template: "react", "react-ts", "vanilla", "vanilla-ts" */
	template?: "react" | "react-ts" | "vanilla" | "vanilla-ts";
	/** Höhe der Preview */
	height?: number;
}

export function SandpackPreview({
	files,
	template = "react",
	height = 300,
}: SandpackPreviewProps) {
	const [showCode, setShowCode] = useState(false);

	return (
		<div className="my-2 rounded-lg border border-border/50 overflow-hidden">
			<div className="flex items-center justify-between px-3 py-1.5 bg-muted/60 border-b border-border/40">
				<span className="text-[10px] font-mono text-muted-foreground">
					Live Preview
				</span>
				<button
					type="button"
					onClick={() => setShowCode(!showCode)}
					className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
				>
					{showCode ? (
						<>
							<Eye className="h-3 w-3" />
							<span>Preview</span>
						</>
					) : (
						<>
							<Code className="h-3 w-3" />
							<span>Code</span>
						</>
					)}
				</button>
			</div>
			<SandpackProvider
				template={template}
				files={files}
				theme="dark"
				options={{ activeFile: Object.keys(files)[0] }}
			>
				{showCode ? (
					<SandpackCodeEditor
						style={{ height }}
						showLineNumbers
						showTabs
					/>
				) : (
					<SandpackPreviewPane
						style={{ height }}
						showOpenInCodeSandbox={false}
						showRefreshButton
					/>
				)}
			</SandpackProvider>
		</div>
	);
}
