import { z } from "zod";

/**
 * A2UI tree envelope validation — guards against:
 *   - Malformed LLM output (wrong case, string-not-object, missing fields)
 *   - Unknown component types (prevents "Unknown widget" ambiguity)
 *   - Prompt-injection vectors via unsanitized component types
 *
 * Whitelist matches @copilotkit/a2ui-renderer basicCatalog (v0.9).
 */

const ALLOWED_TYPES = [
	"Card",
	"Column",
	"Row",
	"List",
	"Text",
	"Image",
	"Icon",
	"Video",
	"AudioPlayer",
	"Button",
	"TextField",
	"CheckBox",
	"ChoicePicker",
	"Slider",
	"DateTimeInput",
	"Divider",
	"Modal",
	"Tabs",
	"Chart",
] as const;

const allowedTypesSet = new Set<string>(ALLOWED_TYPES);

const nodeSchema: z.ZodType<{ type: string; [key: string]: unknown }> = z.lazy(() =>
	z.object({ type: z.string() }).passthrough(),
);

const envelopeSchema = z.object({
	type: z.literal("a2ui"),
	surface_id: z.string().min(1),
	tree: nodeSchema,
});

export type A2uiEnvelope = z.infer<typeof envelopeSchema>;

type ParseResult =
	| { ok: true; surfaceId: string; tree: Record<string, unknown> }
	| { ok: false; error: string };

/**
 * Validate an A2UI envelope from a tool-result.
 */
export function parseA2uiEnvelope(input: unknown): ParseResult {
	const parsed = envelopeSchema.safeParse(input);
	if (!parsed.success) {
		return { ok: false, error: parsed.error.message };
	}
	const { surface_id, tree } = parsed.data;
	if (!tree || typeof tree !== "object" || Array.isArray(tree)) {
		return { ok: false, error: "tree must be a non-empty object" };
	}
	const treeObj = tree as Record<string, unknown>;
	if (Object.keys(treeObj).length === 0) {
		return { ok: false, error: "tree is empty" };
	}

	const checkNode = (node: unknown): string | null => {
		if (!node || typeof node !== "object" || Array.isArray(node)) {
			return "non-object node";
		}
		const obj = node as Record<string, unknown>;
		const t = obj.type;
		if (typeof t !== "string") return "node missing type string";
		if (!allowedTypesSet.has(t)) return `unknown component type: ${t}`;
		const children = obj.children;
		if (Array.isArray(children)) {
			for (const child of children) {
				const err = checkNode(child);
				if (err) return err;
			}
		}
		return null;
	};

	const err = checkNode(treeObj);
	if (err) return { ok: false, error: err };

	return { ok: true, surfaceId: surface_id, tree: treeObj };
}
