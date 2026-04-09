"use client";

import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import ShikiHighlighter from "react-shiki";
import rehypeParse from "rehype-parse";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import rehypeStringify from "rehype-stringify";
import remarkGfm from "remark-gfm";
import { unified } from "unified";
import type { ResolvedMessage } from "@/lib/matrix/types";

// QW-1 Fix: Matrix-Spec erlaubte CSS-Properties filtern
function filterMatrixStyle(value: string): string {
	const allowedProps = new Set([
		"color",
		"background-color",
		"font-weight",
		"font-style",
		"text-decoration",
	]);
	return value
		.split(";")
		.map((d) => d.trim())
		.filter((d) => {
			const p = d.split(":")[0]?.trim().toLowerCase();
			return p && allowedProps.has(p);
		})
		.join("; ");
}

const sanitizeSchema = {
	...defaultSchema,
	attributes: {
		...defaultSchema.attributes,
		code: [...(defaultSchema.attributes?.code ?? []), "className"],
		span: [...(defaultSchema.attributes?.span ?? []), "className", "style"],
	},
	allowDangerousHtml: false,
};

const htmlProcessor = unified()
	.use(rehypeParse, { fragment: true })
	.use(rehypeSanitize, sanitizeSchema)
	.use(rehypeStringify);

/** Parse matrix.to permalink into type + ID */
function parseMatrixPermalink(
	url: string,
): { type: "user" | "room" | "event"; id: string; eventId?: string } | null {
	const match = url.match(/^https?:\/\/matrix\.to\/#\/([^?]+)/);
	if (!match?.[1]) return null;
	const fragment = decodeURIComponent(match[1]);
	if (fragment.startsWith("@")) return { type: "user", id: fragment };
	if (fragment.startsWith("!")) {
		const parts = fragment.split("/");
		if (parts[1]?.startsWith("$")) return { type: "event", id: parts[0], eventId: parts[1] };
		return { type: "room", id: parts[0] };
	}
	if (fragment.startsWith("#")) return { type: "room", id: fragment };
	return null;
}

function linkifyText(text: string): (string | React.ReactElement)[] {
	const urlRegex = /https?:\/\/[^\s<>"{}|\\^[\]`]+/g;
	const parts: (string | React.ReactElement)[] = [];
	let lastIndex = 0;
	for (const match of text.matchAll(urlRegex)) {
		const idx = match.index ?? 0;
		if (idx > lastIndex) parts.push(text.slice(lastIndex, idx));

		const permalink = parseMatrixPermalink(match[0]);
		if (permalink) {
			// Matrix permalink → In-App Navigation
			const label =
				permalink.type === "user"
					? (permalink.id.split(":")[0]?.replace("@", "") ?? permalink.id)
					: permalink.type === "room"
						? permalink.id
						: "Nachricht";
			parts.push(
				<button
					key={idx}
					type="button"
					className="text-primary hover:underline font-medium inline"
					onClick={() => {
						// Dispatch custom event fuer MatrixChat Navigation
						window.dispatchEvent(new CustomEvent("matrix:navigate", { detail: permalink }));
					}}
				>
					{permalink.type === "user"
						? `@${label}`
						: permalink.type === "room"
							? permalink.id
							: `↗ ${label}`}
				</button>,
			);
		} else {
			parts.push(
				<a
					key={idx}
					href={match[0]}
					target="_blank"
					rel="noopener noreferrer"
					className="text-blue-400 hover:underline"
				>
					{match[0]}
				</a>,
			);
		}
		lastIndex = idx + match[0].length;
	}
	if (lastIndex < text.length) parts.push(text.slice(lastIndex));
	return parts;
}

const markdownComponents: React.ComponentProps<typeof ReactMarkdown>["components"] = {
	code({ className, children, ...props }) {
		const match = /language-(\w+)/.exec(className ?? "");
		const value = String(children).replace(/\n$/, "");
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

		return (
			<ShikiHighlighter
				language={match?.[1] ?? "text"}
				theme="one-dark-pro"
				className="text-xs leading-relaxed !bg-transparent !m-0 !rounded-none"
			>
				{value}
			</ShikiHighlighter>
		);
	},
	pre({ children }) {
		return (
			<div className="my-2 rounded-md border border-border/50 overflow-hidden">{children}</div>
		);
	},
};

export function TextContent({ message }: { message: ResolvedMessage }) {
	const sanitizedHtml = useMemo(() => {
		if (!message.formattedBody) return null;
		const styleFiltered = message.formattedBody.replace(/style="([^"]*)"/g, (_, styles: string) => {
			const filtered = filterMatrixStyle(styles);
			return filtered ? `style="${filtered}"` : "";
		});
		return String(htmlProcessor.processSync(styleFiltered));
	}, [message.formattedBody]);

	if (sanitizedHtml !== null) {
		return (
			<div
				className="prose prose-sm dark:prose-invert max-w-none break-words"
				// biome-ignore lint/security/noDangerouslySetInnerHtml: sanitized by rehype-sanitize
				dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
			/>
		);
	}
	if (message.isBot) {
		return (
			<div className="prose prose-sm dark:prose-invert max-w-none break-words">
				<ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
					{message.body}
				</ReactMarkdown>
			</div>
		);
	}
	return <p className="whitespace-pre-wrap break-words text-sm">{linkifyText(message.body)}</p>;
}

export function NoticeContent({ message }: { message: ResolvedMessage }) {
	return (
		<p className="whitespace-pre-wrap break-words text-sm italic text-muted-foreground">
			{message.body}
		</p>
	);
}

export function EmoteContent({ message }: { message: ResolvedMessage }) {
	return (
		<p className="whitespace-pre-wrap break-words text-sm italic">
			<span className="font-medium not-italic">{message.senderDisplayName}</span> {message.body}
		</p>
	);
}
