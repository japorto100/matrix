"use client";

// AddMemoryModal — Tabbed dialog for adding memories
// Pattern adopted from _ref/supermemory/apps/web/components/add-document/index.tsx
// Tabs: Note · Link · File · Bridge
// (Bridge replaces supermemory's "Connect" — for us it's NATS subject bridges
//  to Memory Engine, planned for exec-05b. Connect tab in supermemory was
//  Google Drive / Notion / OneDrive OAuth.)

import { FileUp, Globe, Link2, NotebookPen, Radio } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { UploadDropzone } from "@/features/files/components/UploadDropzone";
import { useIngestDocument, useIngestLink, useIngestNote } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import { NoteEditor, type NoteEditorRef } from "./NoteEditor";

interface AddMemoryModalProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	defaultTab?: "note" | "link" | "file" | "bridge";
}

type IngestTarget = "memory" | "sandbox" | "storage";

const TARGETS: { value: IngestTarget; label: string; description: string }[] = [
	{
		value: "memory",
		label: "Hindsight Memory",
		description: "Index into Hindsight (default)",
	},
	{
		value: "sandbox",
		label: "Agent Sandbox",
		description: "Available for agent code execution",
	},
	{
		value: "storage",
		label: "Object Storage Only",
		description: "SeaweedFS, no processing",
	},
];

function TargetSelector({
	value,
	onChange,
}: {
	value: IngestTarget;
	onChange: (v: IngestTarget) => void;
}) {
	return (
		<div className="border border-border rounded-lg p-2 bg-muted/20">
			<p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80 mb-1.5 px-1">
				Upload Target
			</p>
			<div className="grid grid-cols-3 gap-1.5">
				{TARGETS.map((t) => (
					<button
						key={t.value}
						type="button"
						onClick={() => onChange(t.value)}
						className={cn(
							"text-left px-2 py-1.5 rounded-md transition-colors",
							"border",
							value === t.value
								? "border-primary/50 bg-primary/10"
								: "border-transparent hover:bg-accent/30",
						)}
					>
						<p className="text-[11px] font-semibold">{t.label}</p>
						<p className="text-[9px] text-muted-foreground/80 leading-tight mt-0.5">
							{t.description}
						</p>
					</button>
				))}
			</div>
		</div>
	);
}

// ── Note Tab ──────────────────────────────────────────────────────────────

function NoteTab({ target, onDone }: { target: IngestTarget; onDone: () => void }) {
	const editorRef = useRef<NoteEditorRef>(null);
	const [isEmpty, setIsEmpty] = useState(true);
	const ingestNote = useIngestNote();

	const handleSave = async () => {
		const content = editorRef.current?.getHTML() ?? "";
		if (!content || content === "<p></p>") return;
		try {
			const result = await ingestNote.mutateAsync({
				text: content,
				tags: [`target:${target}`, "note"],
			});
			toast.success(
				result.status === "ok"
					? `Note saved (${result.chunks ?? 0} chunks)`
					: result.status === "dedup_skip"
						? "Duplicate note — skipped"
						: "Note queued",
			);
			onDone();
		} catch (err) {
			toast.error(`Failed to save note: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

	return (
		<div className="flex flex-col gap-3 pt-2">
			<NoteEditor
				ref={editorRef}
				autoFocus
				placeholder="Write a note to remember..."
				onUpdate={setIsEmpty}
				onSubmit={handleSave}
				minHeight="200px"
				maxHeight="400px"
			/>
			<div className="flex items-center justify-between gap-3">
				<p className="text-[10px] font-mono text-muted-foreground/70">⌘+Enter to save</p>
				<Button onClick={handleSave} disabled={isEmpty || ingestNote.isPending} size="sm">
					{ingestNote.isPending ? "Saving..." : "Save Note"}
				</Button>
			</div>
		</div>
	);
}

// ── Link Tab ──────────────────────────────────────────────────────────────

function LinkTab({ target, onDone }: { target: IngestTarget; onDone: () => void }) {
	const [url, setUrl] = useState("");
	const [title, setTitle] = useState("");
	const ingestLink = useIngestLink();

	const handleAdd = async () => {
		if (!url) return;
		try {
			await ingestLink.mutateAsync({
				url,
				title: title || undefined,
				tags: [`target:${target}`, "link"],
			});
			toast.success("Link queued for ingestion");
			setUrl("");
			setTitle("");
			onDone();
		} catch (err) {
			toast.error(`Failed to queue link: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

	return (
		<div className="flex flex-col gap-3 pt-2">
			<div className="space-y-1.5">
				<label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80">
					URL
				</label>
				<Input
					type="url"
					placeholder="https://..."
					value={url}
					onChange={(e) => setUrl(e.target.value)}
				/>
			</div>
			<div className="space-y-1.5">
				<label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80">
					Title (optional — auto-extracted from page)
				</label>
				<Input
					type="text"
					placeholder="Will use OG tag if empty"
					value={title}
					onChange={(e) => setTitle(e.target.value)}
				/>
			</div>
			<div className="flex items-center justify-between gap-3 pt-1">
				<p className="text-[10px] font-mono text-muted-foreground/70">
					Page content will be scraped + chunked + embedded
				</p>
				<Button onClick={handleAdd} disabled={!url || ingestLink.isPending} size="sm">
					{ingestLink.isPending ? "Adding..." : "Add Link"}
				</Button>
			</div>
		</div>
	);
}

// ── File Tab (reuses files_surface UploadDropzone) ────────────────────────

function FileTab({ target, onDone }: { target: IngestTarget; onDone: () => void }) {
	const ingestDocument = useIngestDocument();

	const handleUploaded = async ({ filename, fileId }: { filename: string; fileId: string }) => {
		if (target === "storage") {
			toast.success(`Uploaded ${filename} (storage only)`);
			return;
		}
		if (!fileId) {
			toast.warning(`Uploaded ${filename} but no file_id returned — ingestion skipped`);
			return;
		}
		try {
			await ingestDocument.mutateAsync({
				file_id: fileId,
				tags: [`target:${target}`, "file"],
			});
			toast.success(`Uploaded + queued ${filename} for ingestion`);
			onDone();
		} catch (err) {
			toast.error(`Upload ok, ingest failed: ${err instanceof Error ? err.message : "unknown"}`);
		}
	};

	return (
		<div className="flex flex-col gap-3 pt-2">
			<UploadDropzone onUploaded={handleUploaded} />
			<p className="text-[10px] text-muted-foreground/70 px-1">
				Files are uploaded to SeaweedFS via signed URL, then auto-routed to Hindsight Memory for
				chunking + embedding (unless target = storage only).
			</p>
		</div>
	);
}

// ── Bridge Tab (NATS message bridges, replaces supermemory's "Connect") ───

function BridgeTab() {
	const BRIDGES = [
		{
			id: "matrix",
			label: "Matrix Rooms",
			icon: Radio,
			status: "active",
			subject: "matrix.message.inbound",
			description: "Routes Matrix room messages → Hindsight Memory",
		},
		{
			id: "slack",
			label: "Slack",
			icon: Radio,
			status: "planned",
			subject: "slack.message.inbound",
			description: "exec-05b — coming soon",
		},
		{
			id: "discord",
			label: "Discord",
			icon: Radio,
			status: "planned",
			subject: "discord.message.inbound",
			description: "exec-05b — coming soon",
		},
		{
			id: "telegram",
			label: "Telegram",
			icon: Radio,
			status: "planned",
			subject: "telegram.message.inbound",
			description: "exec-05b — coming soon",
		},
	];

	return (
		<div className="flex flex-col gap-2 pt-2">
			<p className="text-[10px] text-muted-foreground/70 px-1">
				Configure NATS message bridges that auto-ingest into Hindsight Memory. Bridges run
				server-side; toggle below activates the consumer.
			</p>
			<div className="space-y-2">
				{BRIDGES.map((bridge) => {
					const Icon = bridge.icon;
					const isActive = bridge.status === "active";
					return (
						<div
							key={bridge.id}
							className={cn(
								"border rounded-lg px-3 py-2.5 flex items-center justify-between gap-3",
								isActive
									? "bg-emerald-500/5 border-emerald-500/30"
									: "bg-muted/20 border-border opacity-70",
							)}
						>
							<div className="flex items-center gap-2.5 flex-1 min-w-0">
								<Icon
									className={cn(
										"h-4 w-4 shrink-0",
										isActive ? "text-emerald-400" : "text-muted-foreground",
									)}
								/>
								<div className="flex-1 min-w-0">
									<div className="flex items-center gap-2">
										<p className="text-sm font-semibold">{bridge.label}</p>
										<span
											className={cn(
												"text-[9px] font-mono px-1.5 py-0.5 rounded",
												isActive
													? "bg-emerald-500/20 text-emerald-400"
													: "bg-muted text-muted-foreground",
											)}
										>
											{bridge.status}
										</span>
									</div>
									<p className="text-[10px] text-muted-foreground font-mono">{bridge.subject}</p>
									<p className="text-[10px] text-muted-foreground/70">{bridge.description}</p>
								</div>
							</div>
						</div>
					);
				})}
			</div>
		</div>
	);
}

// ── Modal Wrapper ─────────────────────────────────────────────────────────

export function AddMemoryModal({ open, onOpenChange, defaultTab = "note" }: AddMemoryModalProps) {
	const [target, setTarget] = useState<IngestTarget>("memory");
	const handleDone = () => onOpenChange(false);

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="sm:max-w-[640px] max-h-[85vh] overflow-y-auto">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<NotebookPen className="h-4 w-4" />
						Add Memory
					</DialogTitle>
				</DialogHeader>

				<div className="space-y-3 mt-2">
					<TargetSelector value={target} onChange={setTarget} />

					<Tabs defaultValue={defaultTab} className="w-full">
						<TabsList className="grid w-full grid-cols-4">
							<TabsTrigger value="note" className="gap-1.5">
								<NotebookPen className="h-3 w-3" />
								<span>Note</span>
							</TabsTrigger>
							<TabsTrigger value="link" className="gap-1.5">
								<Link2 className="h-3 w-3" />
								<span>Link</span>
							</TabsTrigger>
							<TabsTrigger value="file" className="gap-1.5">
								<FileUp className="h-3 w-3" />
								<span>File</span>
							</TabsTrigger>
							<TabsTrigger value="bridge" className="gap-1.5">
								<Globe className="h-3 w-3" />
								<span>Bridge</span>
							</TabsTrigger>
						</TabsList>

						<TabsContent value="note">
							<NoteTab target={target} onDone={handleDone} />
						</TabsContent>
						<TabsContent value="link">
							<LinkTab target={target} onDone={handleDone} />
						</TabsContent>
						<TabsContent value="file">
							<FileTab target={target} onDone={handleDone} />
						</TabsContent>
						<TabsContent value="bridge">
							<BridgeTab />
						</TabsContent>
					</Tabs>
				</div>
			</DialogContent>
		</Dialog>
	);
}
