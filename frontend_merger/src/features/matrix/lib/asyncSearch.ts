/**
 * Generischer Fuzzy-Search-Helper fuer Listen-Filter in der UI.
 *
 * Case-insensitive Substring-Match mit Whitespace-Normalisierung: der Query
 * wird an Leerzeichen getrennt, jedes Token muss in mindestens einem
 * searchField vorkommen (AND-Semantik). Das matcht Cinny's AsyncSearch-Pattern,
 * aber eigenstaendig reimplementiert (AGPL-Disziplin).
 *
 * Verwendung:
 *   const search = createAsyncSearch<Member>({
 *     searchFields: (m) => [m.displayName, m.userId],
 *   });
 *   const filtered = search(query, members);
 *
 * Bei leerer/whitespace-only Query: gibt die Originalliste zurueck.
 */

export interface AsyncSearchOptions<T> {
	/** Extractor fuer durchsuchbare Strings pro Item. Mehrere Felder = OR-Match pro Token. */
	searchFields: (item: T) => Array<string | undefined | null>;
	/**
	 * Optional: Normalisierer fuer Query und Feld-Werte (default: lowercase + trim
	 * + Whitespace-Collapse). Wird auf beide Seiten angewendet.
	 */
	normalize?: (s: string) => string;
}

export type AsyncSearchFn<T> = (query: string, items: T[]) => T[];

const defaultNormalize = (s: string): string => s.toLowerCase().trim().replace(/\s+/g, " ");

export function createAsyncSearch<T>(opts: AsyncSearchOptions<T>): AsyncSearchFn<T> {
	const normalize = opts.normalize ?? defaultNormalize;
	return (query, items) => {
		const normQuery = normalize(query);
		if (!normQuery) return items;

		const tokens = normQuery.split(" ").filter(Boolean);
		if (tokens.length === 0) return items;

		return items.filter((item) => {
			const fields = opts
				.searchFields(item)
				.map((v) => (typeof v === "string" ? normalize(v) : ""))
				.filter((v) => v.length > 0);

			// Jedes Token muss in mindestens einem Feld vorkommen (AND ueber Tokens, OR ueber Felder).
			return tokens.every((token) => fields.some((field) => field.includes(token)));
		});
	};
}
