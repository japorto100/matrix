/**
 * Tiptap Mention/Room Suggestion Configs.
 *
 * Zwei Trigger:
 *   @ → User/Agent/@room Mentions (MentionList)
 *   # → Room-Pills (RoomMentionList)
 *
 * Separiert von den UI-Komponenten für Testbarkeit.
 */

import type { MemberInfo } from "@matrix/lib/hooks/useRoomMembers";
import { isAgentUser } from "@matrix/lib/resolvers";
import type { RoomInfo } from "@matrix/lib/types";
import type { Editor } from "@tiptap/core";
import type { MentionOptions } from "@tiptap/extension-mention";
import type { ReactRenderer } from "@tiptap/react";
import type { SuggestionKeyDownProps } from "@tiptap/suggestion";
import type { MentionItem, MentionListRef } from "./MentionList";

// ─── Shared render factory ──────────────────────────────────────────────────

function createPopupRenderer() {
	return () => {
		let renderer: ReactRenderer<MentionListRef> | null = null;
		let popup: HTMLDivElement | null = null;

		return {
			onStart: (props: { editor: Editor; clientRect?: (() => DOMRect | null) | null }) => {
				import("@tiptap/react").then(({ ReactRenderer: RR }) => {
					import("./MentionList").then(({ MentionList }) => {
						renderer = new RR(MentionList, {
							props,
							editor: props.editor,
						});

						popup = document.createElement("div");
						popup.style.position = "absolute";
						popup.style.zIndex = "50";
						popup.appendChild(renderer.element);
						document.body.appendChild(popup);

						if (props.clientRect) {
							const rect =
								typeof props.clientRect === "function" ? props.clientRect() : props.clientRect;
							if (rect) {
								popup.style.left = `${rect.left}px`;
								popup.style.top = `${rect.top - 8}px`;
								popup.style.transform = "translateY(-100%)";
							}
						}
					});
				});
			},

			onUpdate: (props: { clientRect?: (() => DOMRect | null) | null }) => {
				renderer?.updateProps(props);
				if (popup && props.clientRect) {
					const rect =
						typeof props.clientRect === "function" ? props.clientRect() : props.clientRect;
					if (rect) {
						popup.style.left = `${rect.left}px`;
						popup.style.top = `${rect.top - 8}px`;
					}
				}
			},

			onKeyDown: (props: SuggestionKeyDownProps) => {
				if (props.event.key === "Escape") {
					popup?.remove();
					renderer?.destroy();
					popup = null;
					renderer = null;
					return true;
				}
				return renderer?.ref?.onKeyDown(props) ?? false;
			},

			onExit: () => {
				popup?.remove();
				renderer?.destroy();
				popup = null;
				renderer = null;
			},
		};
	};
}

// ─── @ User/Agent Mentions ──────────────────────────────────────────────────

interface CreateUserSuggestionOptions {
	getMembers: () => MemberInfo[];
	myUserId: string;
}

/**
 * @ Trigger — User-Mentions, Agent-Mentions, @room.
 * @room ist ein spezieller Eintrag der alle Raum-Mitglieder benachrichtigt (MSC3952: m.mentions.room = true).
 */
export function createUserMentionSuggestion({
	getMembers,
	myUserId,
}: CreateUserSuggestionOptions): MentionOptions["suggestion"] {
	return {
		items: ({ query }): MentionItem[] => {
			const members = getMembers();
			const q = query.toLowerCase();

			// @room Eintrag — benachrichtigt alle (MSC3952)
			const roomItem: MentionItem = {
				id: "@room",
				label: "room",
				isRoom: true,
			};

			const userItems: MentionItem[] = members
				.filter((m) => m.userId !== myUserId)
				.filter(
					(m) => m.displayName.toLowerCase().includes(q) || m.userId.toLowerCase().includes(q),
				)
				.slice(0, 7)
				.map((m) => ({
					id: m.userId,
					label: m.displayName,
					avatarUrl: m.avatarUrl,
					isAgent: isAgentUser(m.userId),
				}));

			// @room nur zeigen wenn Query passt
			const showRoom = "room".includes(q);
			return showRoom ? [roomItem, ...userItems] : userItems;
		},
		render: createPopupRenderer(),
	};
}

// ─── # Room Pills ───────────────────────────────────────────────────────────

interface CreateRoomSuggestionOptions {
	getRooms: () => RoomInfo[];
	currentRoomId: string;
}

/**
 * # Trigger — Room-Pills (Permalinks zu anderen Räumen).
 * Kein m.mentions-Eintrag, nur ein HTML-Link im formatted_body.
 */
export function createRoomPillSuggestion({
	getRooms,
	currentRoomId,
}: CreateRoomSuggestionOptions): MentionOptions["suggestion"] {
	return {
		char: "#",
		items: ({ query }): MentionItem[] => {
			const rooms = getRooms();
			const q = query.toLowerCase();
			return rooms
				.filter((r) => r.roomId !== currentRoomId && r.membership === "join" && !r.dmUserId)
				.filter((r) => r.name.toLowerCase().includes(q))
				.slice(0, 8)
				.map((r) => ({
					id: r.roomId,
					label: r.name,
					isRoomPill: true,
				}));
		},
		render: createPopupRenderer(),
	};
}
