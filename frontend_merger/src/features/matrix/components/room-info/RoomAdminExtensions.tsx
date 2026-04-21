"use client";

import { useAlive } from "@matrix/lib/hooks/useAlive";
import { Copy, Plus, Trash2 } from "lucide-react";
import type { MatrixClient, Room } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";

interface Props {
	client: MatrixClient;
	roomId: string;
	canEdit: boolean;
}

const JOIN_RULE_OPTIONS = [
	{ value: "invite", label: "Nur auf Einladung (Standard)" },
	{ value: "public", label: "Öffentlich (jeder kann beitreten)" },
	{ value: "knock", label: "Klopfen (Beitritt anfragen)" },
	{ value: "restricted", label: "Space-beschränkt" },
];

const HISTORY_VISIBILITY_OPTIONS = [
	{ value: "shared", label: "Geteilt (Standard, ab Join sichtbar)" },
	{ value: "invited", label: "Ab Einladung sichtbar" },
	{ value: "joined", label: "Nur waehrend Mitgliedschaft sichtbar" },
	{ value: "world_readable", label: "Oeffentlich lesbar (jeder)" },
];

/**
 * D8 Admin-Extensions fuer Room-Settings:
 * Join-Rule, History-Visibility, Aliases-Manager.
 *
 * Rendert im G1 "Admin"-Tab. Liest current-state direkt aus Room-State-Events,
 * sendet Updates via `client.sendStateEvent`. `canEdit` entspricht
 * `myPowerLevel >= state_default` (sonst sind die Selects disabled).
 */
export function RoomAdminExtensions({ client, roomId, canEdit }: Props) {
	const alive = useAlive();
	const room: Room | null = client.getRoom(roomId);

	const initialJoinRule =
		(room?.currentState.getStateEvents("m.room.join_rules", "")?.getContent()?.join_rule as
			| string
			| undefined) ?? "invite";
	const initialHistoryVis =
		(room?.currentState.getStateEvents("m.room.history_visibility", "")?.getContent()
			?.history_visibility as string | undefined) ?? "shared";

	const [joinRule, setJoinRule] = useState(initialJoinRule);
	const [historyVis, setHistoryVis] = useState(initialHistoryVis);
	const [aliases, setAliases] = useState<string[]>([]);
	const [newAlias, setNewAlias] = useState("");
	const [aliasesLoading, setAliasesLoading] = useState(false);

	const loadAliases = useCallback(async () => {
		setAliasesLoading(true);
		try {
			const result = await client.getLocalAliases(roomId);
			if (alive()) setAliases(result.aliases ?? []);
		} catch (err) {
			console.warn("[admin] getLocalAliases failed:", err);
		} finally {
			if (alive()) setAliasesLoading(false);
		}
	}, [client, roomId, alive]);

	useEffect(() => {
		void loadAliases();
	}, [loadAliases]);

	const handleJoinRuleChange = async (next: string) => {
		setJoinRule(next);
		try {
			// SDK 41 typed sendStateEvent auf `keyof StateEvents`. Matrix-Spec erlaubt aber
			// alle m.room.*-State-Events — Cast ist OK.
			await (
				client.sendStateEvent as (r: string, t: string, c: unknown, s: string) => Promise<unknown>
			)(roomId, "m.room.join_rules", { join_rule: next }, "");
			toast.success("Join-Regel gespeichert.");
		} catch {
			toast.error("Join-Regel konnte nicht gespeichert werden.");
			setJoinRule(initialJoinRule);
		}
	};

	const handleHistoryVisChange = async (next: string) => {
		setHistoryVis(next);
		try {
			await (
				client.sendStateEvent as (r: string, t: string, c: unknown, s: string) => Promise<unknown>
			)(roomId, "m.room.history_visibility", { history_visibility: next }, "");
			toast.success("History-Sichtbarkeit gespeichert.");
		} catch {
			toast.error("History-Sichtbarkeit konnte nicht gespeichert werden.");
			setHistoryVis(initialHistoryVis);
		}
	};

	const handleAddAlias = async () => {
		const trimmed = newAlias.trim();
		if (!trimmed || !trimmed.startsWith("#") || !trimmed.includes(":")) {
			toast.error("Alias muss #alias:server.tld Format haben.");
			return;
		}
		try {
			await client.createAlias(trimmed, roomId);
			toast.success("Alias erstellt.");
			setNewAlias("");
			await loadAliases();
		} catch (err) {
			toast.error(err instanceof Error ? err.message : "Alias konnte nicht erstellt werden.");
		}
	};

	const handleDeleteAlias = async (alias: string) => {
		try {
			await client.deleteAlias(alias);
			toast.success("Alias geloescht.");
			await loadAliases();
		} catch {
			toast.error("Alias konnte nicht geloescht werden.");
		}
	};

	const copyRoomId = () => {
		navigator.clipboard.writeText(roomId);
		toast.success("Raum-ID kopiert.");
	};

	return (
		<div className="space-y-5">
			<div>
				<label className="text-xs font-medium text-muted-foreground mb-1 block">Join-Regel</label>
				<Select value={joinRule} onValueChange={handleJoinRuleChange} disabled={!canEdit}>
					<SelectTrigger className="h-8 text-xs">
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{JOIN_RULE_OPTIONS.map((opt) => (
							<SelectItem key={opt.value} value={opt.value} className="text-xs">
								{opt.label}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
				{joinRule === "restricted" && (
					<p className="text-[10px] text-muted-foreground mt-1">
						Hinweis: Restricted benoetigt zusaetzliche `allow`-Config via State-Event.
					</p>
				)}
			</div>

			<div>
				<label className="text-xs font-medium text-muted-foreground mb-1 block">
					History-Sichtbarkeit
				</label>
				<Select value={historyVis} onValueChange={handleHistoryVisChange} disabled={!canEdit}>
					<SelectTrigger className="h-8 text-xs">
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{HISTORY_VISIBILITY_OPTIONS.map((opt) => (
							<SelectItem key={opt.value} value={opt.value} className="text-xs">
								{opt.label}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
			</div>

			<div>
				<label className="text-xs font-medium text-muted-foreground mb-1 block">
					Aliase {aliasesLoading && "…"}
				</label>
				<div className="flex flex-col gap-1">
					{aliases.map((alias) => (
						<div key={alias} className="flex items-center gap-2 px-2 py-1 bg-muted/30 rounded">
							<code className="text-[10px] flex-1 truncate">{alias}</code>
							{canEdit && (
								<Button
									variant="ghost"
									size="icon"
									className="h-6 w-6 text-muted-foreground hover:text-destructive"
									onClick={() => void handleDeleteAlias(alias)}
									title="Alias loeschen"
								>
									<Trash2 className="h-3 w-3" />
								</Button>
							)}
						</div>
					))}
					{aliases.length === 0 && !aliasesLoading && (
						<p className="text-[10px] text-muted-foreground">Keine Aliase eingerichtet.</p>
					)}
				</div>
				{canEdit && (
					<div className="flex items-center gap-2 mt-2">
						<Input
							placeholder="#alias:matrix.local"
							value={newAlias}
							onChange={(e) => setNewAlias(e.target.value)}
							className="h-7 text-[10px]"
							onKeyDown={(e) => {
								if (e.key === "Enter") void handleAddAlias();
							}}
						/>
						<Button
							size="sm"
							variant="outline"
							className="shrink-0 h-7 text-xs"
							onClick={() => void handleAddAlias()}
							disabled={!newAlias.trim()}
						>
							<Plus className="h-3 w-3 mr-1" />
							Hinzufuegen
						</Button>
					</div>
				)}
			</div>

			<div>
				<label className="text-xs font-medium text-muted-foreground mb-1 block">Raum-ID</label>
				<div className="flex items-center gap-2">
					<code className="text-[10px] flex-1 truncate bg-muted/30 px-2 py-1 rounded">
						{roomId}
					</code>
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7 shrink-0"
						onClick={copyRoomId}
						title="Kopieren"
					>
						<Copy className="h-3 w-3" />
					</Button>
				</div>
			</div>
		</div>
	);
}
