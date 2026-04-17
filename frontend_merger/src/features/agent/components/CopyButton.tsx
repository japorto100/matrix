"use client";

import { Check, Copy } from "lucide-react";
import { useCallback, useState } from "react";

/** Shared copy-to-clipboard button — used by AgentChatMessage + AgentChatMarkdown CodeBlock. */
export function CopyButton({ text }: { text: string }) {
	const [copied, setCopied] = useState(false);
	const handleCopy = useCallback(() => {
		void navigator.clipboard.writeText(text).then(() => {
			setCopied(true);
			setTimeout(() => setCopied(false), 1500);
		});
	}, [text]);
	return (
		<button
			type="button"
			onClick={handleCopy}
			className="flex items-center gap-1 text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
			title="Copy"
		>
			{copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
		</button>
	);
}
