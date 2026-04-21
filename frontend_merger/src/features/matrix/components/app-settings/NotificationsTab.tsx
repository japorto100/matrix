"use client";

import { useAccountData } from "@matrix/lib/hooks/useAccountData";
import { Plus, Trash2 } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { PushRuleActionName, PushRuleKind, TweakName } from "matrix-js-sdk";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface Props {
	client: MatrixClient;
}

interface ContentRule {
	rule_id: string;
	pattern: string;
	enabled: boolean;
}

interface PushRulesAccountData {
	global?: {
		content?: ContentRule[];
	};
}

/**
 * Globale Benachrichtigungen: Keyword-Matches (content-rules).
 *
 * Per-Room-Notification-Mode ist in RoomInfoPanel-Notifications-Tab (G4).
 * Hier: globale Keywords die ueberall benachrichtigen (z.B. eigener Name,
 * Projekt-Trigger-Wort).
 */
export function NotificationsTab({ client }: Props) {
	const pushRules = useAccountData<PushRulesAccountData>(client, "m.push_rules");
	const contentRules = pushRules?.global?.content ?? [];
	const [newKeyword, setNewKeyword] = useState("");

	const addKeyword = async () => {
		const trimmed = newKeyword.trim();
		if (!trimmed) return;
		try {
			await client.addPushRule("global", PushRuleKind.ContentSpecific, trimmed, {
				pattern: trimmed,
				actions: [
					PushRuleActionName.Notify,
					{ set_tweak: TweakName.Highlight, value: true },
					{ set_tweak: TweakName.Sound, value: "default" },
				],
			});
			toast.success("Stichwort hinzugefuegt.");
			setNewKeyword("");
		} catch {
			toast.error("Stichwort konnte nicht hinzugefuegt werden.");
		}
	};

	const deleteKeyword = async (ruleId: string) => {
		try {
			await client.deletePushRule("global", PushRuleKind.ContentSpecific, ruleId);
			toast.success("Stichwort entfernt.");
		} catch {
			toast.error("Stichwort konnte nicht entfernt werden.");
		}
	};

	return (
		<div className="space-y-4">
			<div>
				<h3 className="text-sm font-semibold">Stichwort-Benachrichtigungen</h3>
				<p className="text-xs text-muted-foreground">
					Benachrichtigt bei jedem Vorkommen dieser Woerter in allen Raeumen (auch ohne @-Mention).
				</p>
			</div>

			<div className="flex flex-col gap-1.5">
				{contentRules.map((rule) => (
					<div
						key={rule.rule_id}
						className="flex items-center gap-2 px-2 py-1.5 bg-muted/30 rounded"
					>
						<span className="text-xs flex-1 truncate">{rule.pattern}</span>
						<Button
							variant="ghost"
							size="icon"
							className="h-6 w-6 text-muted-foreground hover:text-destructive"
							onClick={() => void deleteKeyword(rule.rule_id)}
							title="Entfernen"
						>
							<Trash2 className="h-3 w-3" />
						</Button>
					</div>
				))}
				{contentRules.length === 0 && (
					<p className="text-xs text-muted-foreground">Keine Stichwoerter eingerichtet.</p>
				)}
			</div>

			<div className="flex items-center gap-2">
				<Input
					placeholder="z.B. projekt-x"
					value={newKeyword}
					onChange={(e) => setNewKeyword(e.target.value)}
					className="h-8 text-xs"
					onKeyDown={(e) => {
						if (e.key === "Enter") void addKeyword();
					}}
				/>
				<Button
					size="sm"
					variant="outline"
					onClick={() => void addKeyword()}
					disabled={!newKeyword.trim()}
					className="shrink-0 h-8"
				>
					<Plus className="h-3.5 w-3.5 mr-1" />
					Hinzufuegen
				</Button>
			</div>

			<p className="text-[10px] text-muted-foreground">
				Per-Raum-Benachrichtigungen (Standard / Alle / Nur Erwaehnungen / Stumm) findest du im
				Raum-Info-Panel unter "Benachrichtigungen".
			</p>
		</div>
	);
}
