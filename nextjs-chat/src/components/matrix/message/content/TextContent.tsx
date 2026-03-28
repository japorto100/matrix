"use client";

import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
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

function linkifyText(text: string): (string | React.ReactElement)[] {
	const urlRegex = /https?:\/\/[^\s<>"{}|\\^[\]`]+/g;
	const parts: (string | React.ReactElement)[] = [];
	let lastIndex = 0;
	for (const match of text.matchAll(urlRegex)) {
		const idx = match.index ?? 0;
		if (idx > lastIndex) parts.push(text.slice(lastIndex, idx));
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
		lastIndex = idx + match[0].length;
	}
	if (lastIndex < text.length) parts.push(text.slice(lastIndex));
	return parts;
}

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
				<ReactMarkdown remarkPlugins={[remarkGfm]}>{message.body}</ReactMarkdown>
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
