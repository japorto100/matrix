import { randomBytes, scryptSync, timingSafeEqual } from "node:crypto";

const SCRYPT_N = 1 << 14;
const SCRYPT_R = 8;
const SCRYPT_P = 1;
const KEY_LENGTH = 64;
const HASH_PREFIX = "scrypt";

function normalizePassword(input: string): string {
	return input.normalize("NFKC");
}

export function hashPassword(password: string): string {
	const normalized = normalizePassword(password);
	const salt = randomBytes(16);
	const derivedKey = scryptSync(normalized, salt, KEY_LENGTH, {
		N: SCRYPT_N,
		r: SCRYPT_R,
		p: SCRYPT_P,
	}) as Buffer;
	return [
		HASH_PREFIX,
		String(SCRYPT_N),
		String(SCRYPT_R),
		String(SCRYPT_P),
		salt.toString("base64url"),
		Buffer.from(derivedKey).toString("base64url"),
	].join("$");
}

export function verifyPassword(password: string, encodedHash: string): boolean {
	const parts = encodedHash.split("$");
	if (parts.length !== 6) return false;
	const [prefix, nRaw, rRaw, pRaw, saltB64, hashB64] = parts;
	if (!prefix || !nRaw || !rRaw || !pRaw || !saltB64 || !hashB64) return false;
	if (prefix !== HASH_PREFIX) return false;

	const N = Number.parseInt(nRaw, 10);
	const r = Number.parseInt(rRaw, 10);
	const p = Number.parseInt(pRaw, 10);
	if (!Number.isFinite(N) || !Number.isFinite(r) || !Number.isFinite(p)) return false;

	let salt: Buffer;
	let expected: Buffer;
	try {
		salt = Buffer.from(saltB64, "base64url");
		expected = Buffer.from(hashB64, "base64url");
	} catch {
		return false;
	}
	if (salt.length === 0 || expected.length === 0) return false;

	const normalized = normalizePassword(password);
	let actual: Buffer;
	try {
		actual = scryptSync(normalized, salt, expected.length, { N, r, p }) as Buffer;
	} catch {
		return false;
	}
	if (actual.length !== expected.length) return false;
	return timingSafeEqual(actual, expected);
}

export function validateNewPassword(password: string): { ok: true } | { ok: false; error: string } {
	if (typeof password !== "string") return { ok: false, error: "password is required" };
	if (password.length < 12) return { ok: false, error: "password must be at least 12 characters" };
	if (password.length > 256) return { ok: false, error: "password is too long" };
	return { ok: true };
}
