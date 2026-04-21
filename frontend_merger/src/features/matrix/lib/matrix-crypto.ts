"use client";

import type { CryptoApi } from "matrix-js-sdk/lib/crypto-api";

/**
 * Prueft ob ein Device cross-signed verifiziert ist.
 *
 * Returns:
 *   - `null`  wenn der Status nicht ermittelbar ist (Device nicht gefunden).
 *   - `true`  wenn das Device cross-signed verifiziert ist.
 *   - `false` wenn das Device bekannt aber nicht verifiziert ist.
 *
 * Baustein fuer Send-Decisions (z.B. globalBlacklistUnverifiedDevices,
 * UI-Badges an Devices in MemberList, Pre-Send-Warnungen).
 */
export async function verifiedDevice(
	api: CryptoApi,
	userId: string,
	deviceId: string,
): Promise<boolean | null> {
	const status = await api.getDeviceVerificationStatus(userId, deviceId);
	if (!status) return null;
	return status.crossSigningVerified;
}
