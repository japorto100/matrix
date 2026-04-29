import type { MatrixEvent, Room } from "matrix-js-sdk";
import { type IStateEvent, WidgetParser } from "matrix-widget-api";

export const MATRIX_WIDGET_EVENT_TYPES = ["m.widget", "im.vector.modular.widgets"] as const;

export type MatrixWidgetStatus =
	| "approved"
	| "pending"
	| "blocked"
	| "denied"
	| "revoked"
	| "expired"
	| "unsupported";

export interface MatrixWidgetSummary {
	id: string;
	stateKey?: string;
	name: string;
	type: string;
	url?: string;
	origin?: string;
	status: MatrixWidgetStatus;
	blockedReason?: string;
	fallbackText?: string;
	permissions: string[];
	auditRefs: string[];
	resourceUri?: string;
	descriptorHash?: string;
	expiresAt?: string;
	isIframeAllowed: boolean;
	waitForIframeLoad: boolean;
}

const DEFAULT_ALLOWED_WIDGET_ORIGINS = ["https://widgets.example", "https://widgets.example.test"];

function readString(value: unknown): string | undefined {
	const trimmed = typeof value === "string" ? value.trim() : "";
	return trimmed || undefined;
}

function readStringArray(value: unknown): string[] {
	if (!Array.isArray(value)) return [];
	return value.filter((item): item is string => typeof item === "string" && item.trim() !== "");
}

function readRecord(value: unknown): Record<string, unknown> {
	return value && typeof value === "object" && !Array.isArray(value)
		? (value as Record<string, unknown>)
		: {};
}

export function normalizeWidgetUrl(value: unknown): string | undefined {
	if (typeof value !== "string") return undefined;
	try {
		const url = new URL(value);
		if (url.protocol !== "https:" && url.protocol !== "http:") return undefined;
		return url.toString();
	} catch {
		return undefined;
	}
}

export function widgetOrigin(url: string | undefined): string | undefined {
	if (!url) return undefined;
	try {
		const parsed = new URL(url);
		return parsed.origin;
	} catch {
		return undefined;
	}
}

export function allowedWidgetOrigins(): string[] {
	const configured = process.env.NEXT_PUBLIC_MATRIX_WIDGET_ALLOWED_ORIGINS;
	if (!configured) return DEFAULT_ALLOWED_WIDGET_ORIGINS;
	return configured
		.split(",")
		.map((origin) => origin.trim())
		.filter(Boolean);
}

export function isWidgetOriginAllowed(origin: string | undefined): boolean {
	return !!origin && allowedWidgetOrigins().includes(origin);
}

function getStateKey(ev: MatrixEvent): string | undefined {
	return (ev as MatrixEvent & { getStateKey?: () => string | undefined }).getStateKey?.();
}

function isExpired(expiresAt: string | undefined): boolean {
	if (!expiresAt) return false;
	const time = Date.parse(expiresAt);
	return Number.isFinite(time) && time <= Date.now();
}

function inferWidgetStatus(input: {
	url?: string;
	origin?: string;
	data: Record<string, unknown>;
	content: Record<string, unknown>;
	auditRefs: string[];
	expiresAt?: string;
}): { status: MatrixWidgetStatus; blockedReason?: string; iframeAllowed: boolean } {
	if (!input.url)
		return { status: "blocked", blockedReason: "unsafe-widget-url", iframeAllowed: false };
	if (isExpired(input.expiresAt)) return { status: "expired", iframeAllowed: false };

	const rawStatus =
		readString(input.data.status) ??
		readString(input.data.approval_status) ??
		readString(input.content.status);

	if (rawStatus === "revoked") return { status: "revoked", iframeAllowed: false };
	if (rawStatus === "denied") return { status: "denied", iframeAllowed: false };
	if (rawStatus === "proposed" || rawStatus === "pending") {
		return { status: "pending", iframeAllowed: false };
	}
	if (rawStatus === "blocked")
		return { status: "blocked", blockedReason: "policy-blocked", iframeAllowed: false };

	const originAllowed = isWidgetOriginAllowed(input.origin);
	if (input.auditRefs.length > 0 || rawStatus === "approved") {
		if (!originAllowed) {
			return {
				status: "blocked",
				blockedReason: "widget-origin-not-allowed",
				iframeAllowed: false,
			};
		}
		return { status: "approved", iframeAllowed: true };
	}

	return { status: "unsupported", blockedReason: "missing-policy-approval", iframeAllowed: false };
}

export function parseMatrixWidgetEvent(ev: MatrixEvent): MatrixWidgetSummary | null {
	if (
		!MATRIX_WIDGET_EVENT_TYPES.includes(ev.getType() as (typeof MATRIX_WIDGET_EVENT_TYPES)[number])
	) {
		return null;
	}

	const content = readRecord(ev.getContent());
	const stateKey =
		getStateKey(ev) ??
		readString(content.id) ??
		readString(readRecord(content.data).proposal_id) ??
		readString(readRecord(content.data).proposalId) ??
		ev.getId() ??
		readString(content.name) ??
		"widget";
	const widget = WidgetParser.parseRoomWidget({
		content,
		sender: ev.getSender() ?? "",
		type: ev.getType(),
		state_key: stateKey,
		event_id: ev.getId() ?? "$widget",
		room_id: (ev as MatrixEvent & { getRoomId?: () => string | undefined }).getRoomId?.() ?? "",
		origin_server_ts: ev.getTs(),
	} satisfies IStateEvent);
	const data = readRecord(content.data);
	const url = normalizeWidgetUrl(widget?.templateUrl ?? content.url);
	const origin = widgetOrigin(url);
	const auditRefs = [
		...readStringArray(data.audit_refs),
		...readStringArray(data.auditRefs),
		...readStringArray(content.audit_refs),
	];
	const permissions = readStringArray(data.permissions);
	const expiresAt =
		readString(data.expires_at) ??
		readString(data.expiresAt) ??
		readString(content.expires_at) ??
		readString(content.expiresAt);
	const status = inferWidgetStatus({ url, origin, data, content, auditRefs, expiresAt });
	const name =
		widget?.name ??
		widget?.title ??
		readString(content.name) ??
		readString(content.type) ??
		"Widget";
	const id =
		widget?.id ??
		stateKey ??
		readString(content.id) ??
		readString(data.proposal_id) ??
		readString(data.proposalId) ??
		name;

	return {
		id,
		stateKey,
		name,
		type: readString(content.type) ?? "matrix-widget",
		url,
		origin,
		status: status.status,
		blockedReason: status.blockedReason,
		fallbackText: readString(data.fallback),
		permissions,
		auditRefs,
		resourceUri: readString(data.resource_uri) ?? readString(data.resourceUri),
		descriptorHash: readString(data.descriptor_hash) ?? readString(data.descriptorHash),
		expiresAt,
		isIframeAllowed: status.iframeAllowed,
		waitForIframeLoad: widget?.waitForIframeLoad ?? true,
	};
}

function widgetEventsFromRoom(room: Room, eventType: string): MatrixEvent[] {
	const stateEvents = room.currentState.getStateEvents(eventType as never) as
		| MatrixEvent
		| MatrixEvent[];
	if (Array.isArray(stateEvents)) return stateEvents;
	return stateEvents ? [stateEvents] : [];
}

export function getRoomWidgets(room: Room | null | undefined): MatrixWidgetSummary[] {
	if (!room) return [];
	const widgets = MATRIX_WIDGET_EVENT_TYPES.flatMap((eventType) =>
		widgetEventsFromRoom(room, eventType)
			.map(parseMatrixWidgetEvent)
			.filter((widget): widget is MatrixWidgetSummary => widget !== null),
	);
	const seen = new Set<string>();
	return widgets.filter((widget) => {
		const key = `${widget.id}:${widget.url ?? ""}`;
		if (seen.has(key)) return false;
		seen.add(key);
		return true;
	});
}
