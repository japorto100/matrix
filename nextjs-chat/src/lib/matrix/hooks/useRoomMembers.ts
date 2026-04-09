"use client";

import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { mxcToHttp } from "@/lib/matrix/utils";

export interface MemberInfo {
	userId: string;
	displayName: string;
	powerLevel: number;
	avatarUrl?: string;
}

export function roleLabel(powerLevel: number): string {
	if (powerLevel >= 100) return "Admin";
	if (powerLevel >= 50) return "Moderator";
	return "Mitglied";
}

/**
 * Hook zum Laden von Raum-Mitgliedern via REST API (joined_members)
 * mit SDK-Cache als Fallback.
 * Extrahiert aus RoomInfoPanel (exec-07 Phase 5).
 */
export function useRoomMembers(client: MatrixClient | null, roomId: string | null) {
	const [members, setMembers] = useState<MemberInfo[]>([]);
	const [fetchKey, setFetchKey] = useState(0);
	const refresh = useCallback(() => setFetchKey((k) => k + 1), []);

	// biome-ignore lint/correctness/useExhaustiveDependencies: fetchKey is intentional refresh trigger
	useEffect(() => {
		if (!client || !roomId) {
			setMembers([]);
			return;
		}
		const room = client.getRoom(roomId);
		if (!room) return;

		const plContent = room.currentState.getStateEvents("m.room.power_levels", "")?.getContent();
		const usersDefault = (plContent?.users_default as number) ?? 0;
		const usersMap = plContent?.users as Record<string, number> | undefined;

		(async () => {
			try {
				const { matrixGetJson } = await import("@/lib/matrix/api");
				const data = await matrixGetJson(
					client,
					`/_matrix/client/v3/rooms/${encodeURIComponent(roomId)}/joined_members`,
				);
				const joined =
					(data.joined as Record<string, { display_name?: string; avatar_url?: string }>) ?? {};
				const memberList: MemberInfo[] = Object.entries(joined).map(([userId, info]) => ({
					userId,
					displayName: info.display_name || userId.split(":")[0]?.replace("@", "") || userId,
					powerLevel: usersMap?.[userId] ?? usersDefault,
					avatarUrl: info.avatar_url?.startsWith("mxc://") ? mxcToHttp(info.avatar_url) : undefined,
				}));
				memberList.sort(
					(a, b) => b.powerLevel - a.powerLevel || a.displayName.localeCompare(b.displayName),
				);
				setMembers(memberList);
			} catch {
				// Fallback: SDK-Cache
				const joined = room.getJoinedMembers();
				const memberList: MemberInfo[] = joined.map((m) => ({
					userId: m.userId,
					displayName: m.name || m.userId,
					powerLevel: usersMap?.[m.userId] ?? usersDefault,
					avatarUrl: m.getMxcAvatarUrl()?.startsWith("mxc://")
						? mxcToHttp(m.getMxcAvatarUrl()!)
						: undefined,
				}));
				memberList.sort(
					(a, b) => b.powerLevel - a.powerLevel || a.displayName.localeCompare(b.displayName),
				);
				setMembers(memberList);
			}
		})();
	}, [client, roomId, fetchKey]);

	return { members, refresh };
}
