"use server";

/**
 * SOTA 2026 Password Security Actions
 * Next.js 16 / React 19 Implementation
 */

import { revalidatePath } from "next/cache";
import { authenticator } from "otplib";
import { auth } from "@/lib/auth";
import { hashPassword, validateNewPassword } from "@/lib/server/auth-password";
import { checkRateLimit } from "@/lib/server/rate-limiter";
import { consumePendingTOTPSecret, storePendingTOTPSecret } from "@/lib/server/totp-pending-store";

export interface MFAData {
	secret?: string;
	otpauth?: string;
	recoveryCodes?: string[];
}

export type ChangePasswordResult =
	| { success: true; data?: MFAData }
	| { success: false; error: string; code?: string };

function getGoGatewayUrl(): string {
	return process.env.GO_GATEWAY_INTERNAL_URL || "http://127.0.0.1:9060";
}

async function postGoAuthAction<T>(
	path: string,
	body: Record<string, unknown>,
	headers?: Record<string, string>,
): Promise<T> {
	const response = await fetch(`${getGoGatewayUrl()}${path}`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			...headers,
		},
		body: JSON.stringify(body),
		cache: "no-store",
	});
	const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
	if (!response.ok) {
		const message =
			typeof payload.error === "string" && payload.error.trim() !== ""
				? payload.error
				: `Go auth action failed with ${response.status}`;
		throw new Error(message);
	}
	return payload as T;
}

/**
 * Notify Go Gateway about a user-level revocation event (1.f2)
 */
async function notifyGoUserRevocation(userId: string) {
	try {
		const gatewayUrl = process.env.GO_GATEWAY_INTERNAL_URL || "http://127.0.0.1:9060";
		await fetch(`${gatewayUrl}/api/v1/auth/revocations/user`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Request-ID": `user-rev-${userId}-${Date.now()}`,
			},
			body: JSON.stringify({
				userId,
				revokedBefore: Math.floor(Date.now() / 1000),
			}),
		});
	} catch (error) {
		console.error("FAILED_GO_USER_REVOCATION_SIGNAL", { userId, error: String(error) });
	}
}

/**
 * Elite MFA - Step 1: Initialize TOTP (1.v12)
 */
export async function setupTOTP(): Promise<ChangePasswordResult> {
	const session = await auth();
	if (!session?.user?.id) return { success: false, error: "Unauthorized" };

	const secret = authenticator.generateSecret();
	const otpauth = authenticator.keyuri(
		session.user.email || "user@tradeview",
		"TradeView Fusion",
		secret,
	);

	// C2: Store secret server-side — never roundtrip through client form submission
	storePendingTOTPSecret(session.user.id, secret);

	return {
		success: true,
		data: { secret, otpauth },
	};
}

/**
 * Elite MFA - Step 2: Verify and Enable (1.v12)
 */
export async function enableTOTP(formData: FormData): Promise<ChangePasswordResult> {
	const session = await auth();
	if (!session?.user?.id) return { success: false, error: "Unauthorized" };

	const userId = session.user.id;
	const code = formData.get("code") as string;
	if (!code) return { success: false, error: "Verification code required." };

	// C2: Read secret from server-side store — never accept from client form submission
	const secret = consumePendingTOTPSecret(userId);
	if (!secret) return { success: false, error: "Setup session expired. Please restart MFA setup." };

	const isValid = authenticator.verify({ token: code, secret });
	if (!isValid) return { success: false, error: "Invalid verification code." };

	try {
		const codes = Array.from(
			{ length: 8 },
			() =>
				crypto.randomUUID().split("-")[0]?.toUpperCase() ??
				crypto.randomUUID().slice(0, 8).toUpperCase(),
		);
		await postGoAuthAction<{ success: true }>(
			"/api/v1/auth/actions/totp-enable",
			{
				secret,
				recoveryCodes: codes,
			},
			{
				"X-Auth-User-Id": userId,
			},
		);

		console.info("SECURITY_EVENT_MFA_ENABLED", { userId, severity: "CRITICAL" });

		revalidatePath("/auth/security");
		return { success: true, data: { recoveryCodes: codes } };
	} catch (_error) {
		return { success: false, error: "Failed to persist MFA state." };
	}
}

/**
 * Elite Password Change (1.v8)
 * Requirements: Active Session, Current Password Match, 2026 Entropy Validation
 */
export async function changePassword(
	_state: ChangePasswordResult,
	formData: FormData,
): Promise<ChangePasswordResult> {
	const session = await auth();
	if (!session?.user?.id) {
		return {
			success: false,
			error: "Unauthorized: Authentication required.",
			code: "AUTH_REQUIRED",
		};
	}

	const currentPassword = formData.get("currentPassword") as string;
	const newPassword = formData.get("newPassword") as string;
	const confirmPassword = formData.get("confirmPassword") as string;

	if (!currentPassword || !newPassword || !confirmPassword) {
		return { success: false, error: "All fields are required." };
	}

	if (newPassword !== confirmPassword) {
		return { success: false, error: "New passwords do not match." };
	}

	const validation = validateNewPassword(newPassword);
	if (!validation.ok) {
		return { success: false, error: validation.error };
	}

	try {
		// Security 2026: Prevent reuse of current password
		if (currentPassword === newPassword) {
			return { success: false, error: "New password must be different from the current one." };
		}

		const newHash = hashPassword(newPassword);
		await postGoAuthAction<{ success: true }>(
			"/api/v1/auth/actions/password-change",
			{
				currentPassword,
				newHash,
			},
			{
				"X-Auth-User-Id": session.user.id,
			},
		);

		// SOTA 2026: Elite Cross-Stack Revocation Signal (1.f2)
		await notifyGoUserRevocation(session.user.id);

		// OTel Audit Log (Phase 1.v13)
		console.info("SECURITY_EVENT_PASSWORD_CHANGE", {
			userId: session.user.id,
			severity: "CRITICAL",
			status: "SUCCESS",
			timestamp: new Date().toISOString(),
		});

		revalidatePath("/auth/security");
		return { success: true };
	} catch (error) {
		console.error("FAILED_PASSWORD_CHANGE", {
			userId: session.user.id,
			error: error instanceof Error ? error.message : String(error),
		});
		return { success: false, error: "Internal server error during update." };
	}
}

/**
 * Elite Password Recovery - Step 1: Request Reset (1.v9)
 */
export async function requestPasswordReset(
	_state: ChangePasswordResult,
	formData: FormData,
): Promise<ChangePasswordResult> {
	const email = formData.get("email") as string;
	if (!email) return { success: false, error: "Email is required." };

	// H5: Rate limit — 5 requests per 15 minutes per email
	const rl = checkRateLimit(`pwd-reset:${email.toLowerCase()}`, 5, 15 * 60 * 1000);
	if (!rl.allowed) {
		return { success: false, error: "Too many requests. Please try again later." };
	}

	try {
		const token = crypto.randomUUID();
		const expires = new Date(Date.now() + 3600 * 1000);
		const payload = await postGoAuthAction<{ success: true; userId?: string }>(
			"/api/v1/auth/actions/password-recovery-request",
			{
				identifier: email.toLowerCase(),
				token,
				expiresAt: expires.toISOString(),
			},
		);
		if (!payload.userId) {
			console.warn("RECOVERY_REQUEST_NON_EXISTENT_USER", { email });
			return { success: true };
		}

		// H4: Never log the reset URL — it contains the one-time token and is effectively a credential
		console.info("SECURITY_RECOVERY_TOKEN_GENERATED", {
			severity: "CRITICAL",
			userId: payload.userId,
			message: "Password reset link generated.",
		});

		return { success: true };
	} catch (error) {
		console.error("FAILED_RECOVERY_REQUEST", { email, error: String(error) });
		return { success: false, error: "Failed to process recovery request." };
	}
}

/**
 * Elite Password Recovery - Step 2: Finalize Reset (1.v9)
 */
export async function resetPassword(
	_state: ChangePasswordResult,
	formData: FormData,
): Promise<ChangePasswordResult> {
	const email = formData.get("email") as string;
	const token = formData.get("token") as string;
	const newPassword = formData.get("newPassword") as string;

	if (!email || !token || !newPassword) return { success: false, error: "Invalid reset request." };

	const validation = validateNewPassword(newPassword);
	if (!validation.ok) return { success: false, error: validation.error };

	try {
		const newHash = hashPassword(newPassword);
		const payload = await postGoAuthAction<{ success: true; userId: string }>(
			"/api/v1/auth/actions/password-recovery-reset",
			{
				email: email.toLowerCase(),
				token,
				newHash,
			},
		);

		await notifyGoUserRevocation(payload.userId);

		console.info("SECURITY_EVENT_PASSWORD_RESET_SUCCESS", {
			email,
			severity: "CRITICAL",
			timestamp: new Date().toISOString(),
		});

		return { success: true };
	} catch (error) {
		console.error("FAILED_PASSWORD_RESET", { email, error: String(error) });
		return { success: false, error: "Internal error during reset." };
	}
}

/**
 * Elite Password Recovery - Option 1: Recovery Code (1.v19)
 * Allows resetting password using one of the 8 pre-generated recovery codes.
 */
export async function recoverWithCode(
	_state: ChangePasswordResult,
	formData: FormData,
): Promise<ChangePasswordResult> {
	const email = formData.get("email") as string;
	const recoveryCode = formData.get("recoveryCode") as string;
	const newPassword = formData.get("newPassword") as string;

	if (!email || !recoveryCode || !newPassword) {
		return { success: false, error: "Missing required recovery data." };
	}

	// H5: Rate limit — 5 attempts per 15 minutes per email
	const rl = checkRateLimit(`recovery-code:${email.toLowerCase()}`, 5, 15 * 60 * 1000);
	if (!rl.allowed) {
		return { success: false, error: "Too many requests. Please try again later." };
	}

	const validation = validateNewPassword(newPassword);
	if (!validation.ok) return { success: false, error: validation.error };

	try {
		const newHash = hashPassword(newPassword);
		const payload = await postGoAuthAction<{ success: true; userId: string }>(
			"/api/v1/auth/actions/password-recovery-code",
			{
				email: email.toLowerCase(),
				recoveryCode: recoveryCode.toUpperCase(),
				newHash,
			},
		);

		await notifyGoUserRevocation(payload.userId);

		console.info("SECURITY_EVENT_RECOVERY_CODE_USED", {
			userId: payload.userId,
			severity: "CRITICAL",
			timestamp: new Date().toISOString(),
		});

		return { success: true };
	} catch (error) {
		console.error("FAILED_CODE_RECOVERY", { email, error: String(error) });
		return { success: false, error: "Internal recovery fault." };
	}
}
