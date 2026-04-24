// plan-v2 Phase-2 #32 — Ansatz X A2UI packet types + renderer adapter.
//
// Wire-format mirrors python-backend/agent/streaming.py (camelCase). These
// packets arrive interleaved with text/tool deltas on the agent chat SSE
// stream. A subscriber extracts them before they reach the @ai-sdk zod
// union (which doesn't know the a2ui-* types) and routes them to the
// @copilotkit/a2ui-renderer's processMessages().

// ── Wire types (match Python dataclasses) ────────────────────────────────────

export interface A2uiSurfaceStartPacket {
	type: "a2ui-surface-start";
	surfaceId: string;
	components: unknown;
	dataModel: Record<string, unknown>;
}

export interface A2uiSurfaceUpdatePacket {
	type: "a2ui-update-components";
	surfaceId: string;
	patch: unknown[]; // JSON-Patch array
}

export interface A2uiUpdateDataModelPacket {
	type: "a2ui-update-data-model";
	surfaceId: string;
	patch: unknown[];
}

export interface A2uiSurfaceEndPacket {
	type: "a2ui-surface-end";
	surfaceId: string;
}

export interface A2uiDeleteSurfacePacket {
	type: "a2ui-delete-surface";
	surfaceId: string;
}

export type A2uiPacket =
	| A2uiSurfaceStartPacket
	| A2uiSurfaceUpdatePacket
	| A2uiUpdateDataModelPacket
	| A2uiSurfaceEndPacket
	| A2uiDeleteSurfacePacket;

export const A2UI_PACKET_TYPES = [
	"a2ui-surface-start",
	"a2ui-update-components",
	"a2ui-update-data-model",
	"a2ui-surface-end",
	"a2ui-delete-surface",
] as const;

export function isA2uiPacket(value: unknown): value is A2uiPacket {
	if (!value || typeof value !== "object") return false;
	const t = (value as { type?: unknown }).type;
	return typeof t === "string" && (A2UI_PACKET_TYPES as readonly string[]).includes(t);
}

// ── Adapter: Ansatz X packet → @copilotkit/a2ui-renderer message ────────────
//
// The renderer's processMessages() accepts a union of these shapes in v0.9.
// Our packets map to them 1:1 — this function is pure glue so the SSE
// consumer can forward the translated messages straight into the store.

export interface A2uiRendererMessage {
	version: "v0.9";
	createSurface?: { surfaceId: string; tree: unknown; dataModel?: Record<string, unknown> };
	updateComponents?: { surfaceId: string; patch: unknown[] };
	updateDataModel?: { surfaceId: string; patch: unknown[] };
	endSurface?: { surfaceId: string };
	deleteSurface?: { surfaceId: string };
}

export function toRendererMessage(packet: A2uiPacket): A2uiRendererMessage {
	switch (packet.type) {
		case "a2ui-surface-start":
			return {
				version: "v0.9",
				createSurface: {
					surfaceId: packet.surfaceId,
					tree: packet.components,
					dataModel: packet.dataModel,
				},
			};
		case "a2ui-update-components":
			return {
				version: "v0.9",
				updateComponents: { surfaceId: packet.surfaceId, patch: packet.patch },
			};
		case "a2ui-update-data-model":
			return {
				version: "v0.9",
				updateDataModel: { surfaceId: packet.surfaceId, patch: packet.patch },
			};
		case "a2ui-surface-end":
			return { version: "v0.9", endSurface: { surfaceId: packet.surfaceId } };
		case "a2ui-delete-surface":
			return { version: "v0.9", deleteSurface: { surfaceId: packet.surfaceId } };
	}
}
