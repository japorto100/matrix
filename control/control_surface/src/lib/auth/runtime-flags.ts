export function isAuthEnabled(): boolean {
	return process.env.NEXT_PUBLIC_ENABLE_AUTH === "true";
}

export function isPasskeyProviderEnabled(): boolean {
	const raw = process.env.AUTH_PASSKEY_PROVIDER_ENABLED?.trim().toLowerCase();
	if (raw === "false") return false;
	if (raw === "true") return true;
	return true;
}
