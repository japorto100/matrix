// URL state parsers for control-ui — adopted from
// _ref/supermemory/apps/web/lib/search-params.ts (MIT license).
//
// Pattern: nuqs `parseAs*` with sensible defaults; consumed via useQueryState.
// All client-side modal state + filters live in the URL for shareable / back-button safe UX.

import { parseAsArrayOf, parseAsBoolean, parseAsString, parseAsStringLiteral } from "nuqs";

// ── Add Memory Modal (Slice 5: Content Ingestion) ────────────────────────
export const addMemoryParam = parseAsStringLiteral(["note", "link", "file", "bridge"] as const);

// ── Episode Detail Sheet ─────────────────────────────────────────────────
export const episodeParam = parseAsString;

// ── Memory Filter ────────────────────────────────────────────────────────
const roleLiterals = [
	"fundamentals_analyst",
	"sentiment_analyst",
	"technical_analyst",
	"researcher",
	"trader",
	"risk_manager",
] as const;
export type RoleLiteral = (typeof roleLiterals)[number];

export const rolesParam = parseAsArrayOf(parseAsStringLiteral(roleLiterals), ",").withDefault([]);
export const tagsParam = parseAsArrayOf(parseAsString, ",").withDefault([]);
export const fromParam = parseAsString.withDefault("");
export const toParam = parseAsString.withDefault("");

// ── Search ───────────────────────────────────────────────────────────────
export const searchParam = parseAsBoolean.withDefault(false);
export const qParam = parseAsString.withDefault("");

// ── View Mode (table | grid) ─────────────────────────────────────────────
const viewLiterals = ["grid", "table", "timeline"] as const;
export type ViewLiteral = (typeof viewLiterals)[number];
export const viewParam = parseAsStringLiteral(viewLiterals).withDefault("grid");
