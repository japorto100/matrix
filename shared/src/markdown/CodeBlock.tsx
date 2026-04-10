"use client";

import { Check, Copy } from "lucide-react";
import { useCallback, useState } from "react";
import { ShikiHighlighter } from "react-shiki";

export interface CodeBlockProps {
	language: string;
	value: string;
}

/**
 * Syntax-highlighted code block with copy-to-clipboard.
 * Uses ShikiHighlighter with one-dark-pro theme.
 * Shared between Matrix chat and Agent chat.
 */
export function CodeBlock({ language, value }: CodeBlockProps) {
	const [copied, setCopied] = useState(false);

	const handleCopy = useCallback(() => {
		void navigator.clipboard.writeText(value).then(() => {
			setCopied(true);
			setTimeout(() => setCopied(false), 1500);
		});
	}, [value]);

	return (
		<div className="relative my-2 rounded-md overflow-hidden border border-border/50">
			<div className="flex items-center justify-between px-3 py-1 bg-muted/60 border-b border-border/40">
				<span className="text-[10px] font-mono text-muted-foreground">{language || "text"}</span>
				<button
					type="button"
					onClick={handleCopy}
					className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
				>
					{copied ? (
						<>
							<Check className="h-3 w-3 text-emerald-500" />
							<span className="text-emerald-500">Copied!</span>
						</>
					) : (
						<>
							<Copy className="h-3 w-3" />
							<span>Copy</span>
						</>
					)}
				</button>
			</div>
			<ShikiHighlighter
				language={language || "text"}
				theme="one-dark-pro"
				className="text-xs leading-relaxed !bg-transparent !m-0 !rounded-none"
			>
				{value}
			</ShikiHighlighter>
		</div>
	);
}
