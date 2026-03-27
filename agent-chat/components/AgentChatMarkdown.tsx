"use client";

// Markdown renderer for agent chat messages — Phase 22a / 22f
// AC34: react-markdown + remark-gfm
// AC35: syntax highlighting via react-syntax-highlighter
// AC36: code-block copy button (1.5s feedback)
// AC37: table rendering (GFM)
// AC38: <think> tag collapsible box
// AC39: inline citation rendering [1], [2] → superscript badges

import { Check, ChevronDown, ChevronRight, Copy } from "lucide-react";
import { memo, useCallback, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";

// ---- Think-block collapsible ----

function ThinkBlock({ content }: { content: string }) {
	const [open, setOpen] = useState(false);
	return (
		<div className="my-2 rounded border border-border/60 bg-muted/40 text-xs">
			<button
				type="button"
				onClick={() => setOpen((v) => !v)}
				className="flex w-full items-center gap-1.5 px-3 py-1.5 text-left text-muted-foreground hover:text-foreground transition-colors"
			>
				{open ? (
					<ChevronDown className="h-3 w-3 shrink-0" />
				) : (
					<ChevronRight className="h-3 w-3 shrink-0" />
				)}
				<span className="font-medium">Thinking…</span>
			</button>
			{open && (
				<div className="border-t border-border/40 px-3 py-2 text-muted-foreground whitespace-pre-wrap leading-relaxed">
					{content}
				</div>
			)}
		</div>
	);
}

// ---- AC63: JSON structured-output renderer ----
// Arrays of objects → table; plain objects → key-value card; fallback → CodeBlock.

function JsonRenderer({ value }: { value: string }) {
	const [collapsed, setCollapsed] = useState(false);
	let parsed: unknown;
	try {
		parsed = JSON.parse(value);
	} catch {
		return <CodeBlock language="json" value={value} />;
	}

	// Array of objects → table
	if (
		Array.isArray(parsed) &&
		parsed.length > 0 &&
		typeof parsed[0] === "object" &&
		parsed[0] !== null &&
		!Array.isArray(parsed[0])
	) {
		const headers = Object.keys(parsed[0] as Record<string, unknown>);
		return (
			<div className="my-2 rounded border border-border/50 overflow-hidden">
				<div className="flex items-center justify-between px-3 py-1 bg-muted/60 border-b border-border/40">
					<span className="text-[10px] font-mono text-muted-foreground">
						json · {parsed.length} item{parsed.length !== 1 ? "s" : ""}
					</span>
					<button
						type="button"
						onClick={() => setCollapsed((v) => !v)}
						className="text-muted-foreground hover:text-foreground transition-colors"
						title={collapsed ? "Expand" : "Collapse"}
					>
						{collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
					</button>
				</div>
				{!collapsed && (
					<div className="overflow-x-auto">
						<table className="w-full text-xs border-collapse">
							<thead>
								<tr className="bg-muted/40">
									{headers.map((h) => (
										<th
											key={h}
											className="border border-border/30 px-2 py-1 text-left font-semibold text-muted-foreground font-mono"
										>
											{h}
										</th>
									))}
								</tr>
							</thead>
							<tbody>
								{(parsed as Record<string, unknown>[]).map((row, i) => (
									// biome-ignore lint/suspicious/noArrayIndexKey: stable row index
									<tr key={i} className="even:bg-muted/20">
										{headers.map((h) => (
											<td
												key={h}
												className="border border-border/30 px-2 py-1 text-foreground/80 whitespace-nowrap max-w-[200px] truncate"
											>
												{JSON.stringify(row[h] ?? "")}
											</td>
										))}
									</tr>
								))}
							</tbody>
						</table>
					</div>
				)}
			</div>
		);
	}

	// Plain object → key-value card
	if (typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)) {
		const entries = Object.entries(parsed as Record<string, unknown>);
		return (
			<div className="my-2 rounded border border-border/50 overflow-hidden">
				<div className="flex items-center justify-between px-3 py-1 bg-muted/60 border-b border-border/40">
					<span className="text-[10px] font-mono text-muted-foreground">
						json object · {entries.length} key{entries.length !== 1 ? "s" : ""}
					</span>
					<button
						type="button"
						onClick={() => setCollapsed((v) => !v)}
						className="text-muted-foreground hover:text-foreground transition-colors"
					>
						{collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
					</button>
				</div>
				{!collapsed && (
					<div className="divide-y divide-border/30">
						{entries.map(([k, v]) => (
							<div key={k} className="flex gap-2 px-3 py-1 text-xs">
								<span className="text-muted-foreground font-mono shrink-0 min-w-[80px]">{k}</span>
								<span className="text-foreground/80 break-all">{JSON.stringify(v)}</span>
							</div>
						))}
					</div>
				)}
			</div>
		);
	}

	// Fallback (primitive, empty array, etc.)
	return <CodeBlock language="json" value={value} />;
}

// ---- Code-block with copy ----

function CodeBlock({ language, value }: { language: string; value: string }) {
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
			<SyntaxHighlighter
				style={oneDark}
				language={language || "text"}
				PreTag="div"
				customStyle={{
					margin: 0,
					borderRadius: 0,
					fontSize: "0.75rem",
					lineHeight: "1.5",
					background: "transparent",
				}}
			>
				{value}
			</SyntaxHighlighter>
		</div>
	);
}

// ---- AC39: Citation badge renderer ----
// Transforms [N] text fragments (e.g. [1], [2]) into superscript citation badges.

const CITE_RE = /(\[\d+\])/g;

function renderWithCitations(children: React.ReactNode): React.ReactNode {
	if (typeof children === "string") {
		const parts = children.split(CITE_RE);
		if (parts.length === 1) return children;
		return parts.map((part, i) =>
			CITE_RE.test(part) ? (
				<sup
					// biome-ignore lint/suspicious/noArrayIndexKey: stable citation index
					key={i}
					className="ml-0.5 mr-0.5 inline-flex items-center rounded bg-primary/15 px-0.5 text-[9px] font-mono text-primary/80 leading-tight"
				>
					{part}
				</sup>
			) : (
				part
			),
		);
	}
	if (Array.isArray(children)) {
		return children.map((child, i) =>
			typeof child === "string" ? (
				renderWithCitations(child)
			) : (
				// biome-ignore lint/suspicious/noArrayIndexKey: no stable key available
				<span key={i}>{child}</span>
			),
		);
	}
	return children;
}

// ---- Shared ReactMarkdown components config ----

const markdownComponents: React.ComponentProps<typeof ReactMarkdown>["components"] = {
	code({ className, children, ...props }) {
		const match = /language-(\w+)/.exec(className ?? "");
		const value = String(children).replace(/\n$/, "");
		// AC63: JSON structured renderer for explicit ```json blocks with multi-line content
		if (match?.[1] === "json" && value.includes("\n")) {
			return <JsonRenderer value={value} />;
		}
		if (!match && !value.includes("\n")) {
			return (
				<code
					className="rounded bg-muted px-1 py-0.5 font-mono text-[0.8em] text-foreground"
					{...props}
				>
					{children}
				</code>
			);
		}
		return <CodeBlock language={match?.[1] ?? ""} value={value} />;
	},
	pre({ children }) {
		return <>{children}</>;
	},
	// AC39: apply citation rendering to paragraph text
	p({ children }) {
		return <p className="mb-1 last:mb-0">{renderWithCitations(children)}</p>;
	},
	table({ children }) {
		return (
			<div className="overflow-x-auto my-2">
				<table className="w-full text-xs border-collapse border border-border/40">{children}</table>
			</div>
		);
	},
	th({ children }) {
		return (
			<th className="border border-border/40 bg-muted/60 px-2 py-1 text-left font-semibold text-muted-foreground">
				{children}
			</th>
		);
	},
	td({ children }) {
		return <td className="border border-border/40 px-2 py-1 text-foreground/80">{children}</td>;
	},
	a({ children, href }) {
		return (
			<a
				href={href}
				target="_blank"
				rel="noopener noreferrer"
				className="text-primary underline underline-offset-2 hover:opacity-80"
			>
				{children}
			</a>
		);
	},
	blockquote({ children }) {
		return (
			<blockquote className="border-l-2 border-primary/50 pl-3 text-muted-foreground italic my-2">
				{children}
			</blockquote>
		);
	},
};

// ---- Pre-processor: extract <think> blocks from raw markdown ----

interface Segment {
	type: "markdown" | "think";
	content: string;
	key: string;
}

function splitThinkBlocks(raw: string): Segment[] {
	const segments: Segment[] = [];
	const re = /<think>([\s\S]*?)<\/think>/g;
	let last = 0;
	let pos = 0;

	for (let m = re.exec(raw); m !== null; m = re.exec(raw)) {
		if (m.index > last) {
			segments.push({ type: "markdown", content: raw.slice(last, m.index), key: `md-${pos}` });
			pos++;
		}
		const thinkContent = m[1];
		if (typeof thinkContent === "string") {
			segments.push({ type: "think", content: thinkContent.trim(), key: `think-${pos}` });
			pos++;
		}
		last = m.index + m[0].length;
	}
	if (last < raw.length) {
		segments.push({ type: "markdown", content: raw.slice(last), key: `md-${pos}` });
	}
	return segments;
}

// ---- Main component ----

interface AgentChatMarkdownProps {
	content: string;
}

function AgentChatMarkdownInner({ content }: AgentChatMarkdownProps) {
	const segments = splitThinkBlocks(content);

	return (
		<div className="prose prose-sm prose-invert max-w-none leading-relaxed text-sm text-foreground">
			{segments.map((seg) => {
				if (seg.type === "think") {
					return <ThinkBlock key={seg.key} content={seg.content} />;
				}
				return (
					<ReactMarkdown key={seg.key} remarkPlugins={[remarkGfm]} components={markdownComponents}>
						{seg.content}
					</ReactMarkdown>
				);
			})}
		</div>
	);
}

// AC67: memo — only re-render when content string changes
export const AgentChatMarkdown = memo(AgentChatMarkdownInner);
