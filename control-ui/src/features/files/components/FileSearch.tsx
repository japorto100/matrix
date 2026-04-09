"use client";

// DW12 — FileSearch: fuse.js v7 client-side fuzzy search on document metadata
// v1: searches already-loaded metadata; v1.5: Meilisearch proxy

import Fuse from "fuse.js";
import { Search, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Input } from "@/components/ui/input";

interface FileRecord {
	id: string;
	name: string;
	type: string;
	status: string;
	created_at: string;
}

interface FileSearchProps {
	files: FileRecord[];
	onSelect: (file: FileRecord) => void;
}

export function FileSearch({ files, onSelect }: FileSearchProps) {
	const [query, setQuery] = useState("");

	const fuse = useMemo(
		() =>
			new Fuse(files, {
				keys: ["name", "type"],
				threshold: 0.35,
				includeScore: true,
			}),
		[files],
	);

	const results = query.trim() ? fuse.search(query).map((r) => r.item) : files;

	return (
		<div className="flex flex-col gap-2">
			<div className="relative">
				<Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
				<Input
					value={query}
					onChange={(e) => setQuery(e.target.value)}
					placeholder="Search files…"
					className="pl-8 h-8 text-xs"
				/>
				{query && (
					<button
						onClick={() => setQuery("")}
						className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
					>
						<X className="h-3.5 w-3.5" />
					</button>
				)}
			</div>

			<div className="flex flex-col divide-y divide-border/50 max-h-64 overflow-y-auto">
				{results.length === 0 ? (
					<p className="py-4 text-center text-xs text-muted-foreground/60 italic">
						No files match &ldquo;{query}&rdquo;
					</p>
				) : (
					results.map((file) => (
						<button
							key={file.id}
							onClick={() => onSelect(file)}
							className="flex items-center gap-2 py-1.5 px-1 text-left hover:bg-accent/50 rounded transition-colors"
						>
							<span className="text-xs truncate font-medium flex-1">{file.name}</span>
							<span className="text-[10px] font-mono uppercase text-muted-foreground shrink-0">
								{file.type}
							</span>
						</button>
					))
				)}
			</div>
		</div>
	);
}
