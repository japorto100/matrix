// Shared fetcher helper for useQuery — all tabs use this.
// Returns typed data, throws on non-2xx with formatted error.

export class ApiError extends Error {
	/** Parsed JSON body when the response was JSON (null otherwise).
	 * Lets callers read structured error payloads like ADR-004's
	 * `{suggested_action: "hitl_confirm", rejected: [...]}`. */
	public body: unknown = null;
	constructor(
		public status: number,
		public url: string,
		message: string,
		body?: unknown,
	) {
		super(message);
		if (body !== undefined) this.body = body;
	}
}

async function _readErrorBody(res: Response): Promise<{ text: string; body: unknown }> {
	const text = await res.text().catch(() => "");
	let body: unknown = null;
	if (text) {
		try {
			body = JSON.parse(text);
		} catch {
			body = null;
		}
	}
	return { text, body };
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(path, {
		...init,
		method: "GET",
		headers: {
			accept: "application/json",
			...(init?.headers ?? {}),
		},
		cache: "no-store",
	});
	if (!res.ok) {
		const { text, body } = await _readErrorBody(res);
		throw new ApiError(res.status, path, text || res.statusText, body);
	}
	return (await res.json()) as T;
}

export async function apiPost<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
	const res = await fetch(path, {
		...init,
		method: "POST",
		headers: {
			accept: "application/json",
			"content-type": "application/json",
			...(init?.headers ?? {}),
		},
		body: body === undefined ? null : JSON.stringify(body),
	});
	if (!res.ok) {
		const { text, body } = await _readErrorBody(res);
		throw new ApiError(res.status, path, text || res.statusText, body);
	}
	return (await res.json()) as T;
}

export async function apiPatch<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
	const res = await fetch(path, {
		...init,
		method: "PATCH",
		headers: {
			accept: "application/json",
			"content-type": "application/json",
			...(init?.headers ?? {}),
		},
		body: JSON.stringify(body),
	});
	if (!res.ok) {
		const { text, body } = await _readErrorBody(res);
		throw new ApiError(res.status, path, text || res.statusText, body);
	}
	return (await res.json()) as T;
}

export async function apiPut<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
	const res = await fetch(path, {
		...init,
		method: "PUT",
		headers: {
			accept: "application/json",
			"content-type": "application/json",
			...(init?.headers ?? {}),
		},
		body: JSON.stringify(body),
	});
	if (!res.ok) {
		const { text, body } = await _readErrorBody(res);
		throw new ApiError(res.status, path, text || res.statusText, body);
	}
	return (await res.json()) as T;
}

export async function apiDelete<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(path, {
		...init,
		method: "DELETE",
		headers: {
			accept: "application/json",
			...(init?.headers ?? {}),
		},
	});
	if (!res.ok) {
		const { text, body } = await _readErrorBody(res);
		throw new ApiError(res.status, path, text || res.statusText, body);
	}
	return (await res.json()) as T;
}
