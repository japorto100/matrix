export interface JsonStorageAdapter {
	getJSON<T>(key: string, fallback: T): T;
	setJSON<T>(key: string, value: T): void;
	remove(key: string): void;
}

function canUseBrowserStorage(): boolean {
	return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function createLocalJsonStorageAdapter(prefix: string = "tradeview:"): JsonStorageAdapter {
	const withPrefix = (key: string) => `${prefix}${key}`;

	return {
		getJSON<T>(key: string, fallback: T): T {
			if (!canUseBrowserStorage()) return fallback;
			try {
				const raw = window.localStorage.getItem(withPrefix(key));
				if (!raw) return fallback;
				return JSON.parse(raw) as T;
			} catch {
				return fallback;
			}
		},
		setJSON<T>(key: string, value: T): void {
			if (!canUseBrowserStorage()) return;
			try {
				window.localStorage.setItem(withPrefix(key), JSON.stringify(value));
			} catch {
				// ignore client storage write errors
			}
		},
		remove(key: string): void {
			if (!canUseBrowserStorage()) return;
			try {
				window.localStorage.removeItem(withPrefix(key));
			} catch {
				// ignore client storage remove errors
			}
		},
	};
}

// DB-ready adapter contract: today it falls back to local storage.
// Later this can call a server route (or direct DB service) without changing callers.
export function createDbReadyJsonStorageAdapter(
	fallback: JsonStorageAdapter = createLocalJsonStorageAdapter(),
): JsonStorageAdapter {
	return {
		getJSON<T>(key: string, fallbackValue: T): T {
			return fallback.getJSON(key, fallbackValue);
		},
		setJSON<T>(key: string, value: T): void {
			fallback.setJSON(key, value);
		},
		remove(key: string): void {
			fallback.remove(key);
		},
	};
}
