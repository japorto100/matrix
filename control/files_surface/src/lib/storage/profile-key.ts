const PROFILE_KEY_STORAGE_KEY = "tradeview:profile-key";

export function getClientProfileKey(): string {
	if (typeof window === "undefined") {
		return "server-profile";
	}

	const existing = window.localStorage.getItem(PROFILE_KEY_STORAGE_KEY);
	if (existing) {
		return existing;
	}

	const generated =
		typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
			? crypto.randomUUID()
			: `profile-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

	window.localStorage.setItem(PROFILE_KEY_STORAGE_KEY, generated);
	return generated;
}
