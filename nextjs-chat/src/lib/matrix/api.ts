/**
 * Matrix REST helpers used by the Next.js chat UI.
 *
 * We generally prefer the matrix-js-sdk for correctness and compatibility.
 * This module exists for the small set of endpoints where we intentionally
 * do a direct REST call (e.g. joined_members for fast member lists) while
 * keeping auth + error handling consistent.
 */
import type { MatrixClient } from "matrix-js-sdk";

export class MatrixApiError extends Error {
	status: number;
	bodyText?: string;
	constructor(message: string, status: number, bodyText?: string) {
		super(message);
		this.name = "MatrixApiError";
		this.status = status;
		this.bodyText = bodyText;
	}
}

function getAccessTokenOrThrow(client: MatrixClient): string {
	const token = client.getAccessToken();
	if (!token) throw new Error("Matrix client has no access token");
	return token;
}

async function matrixFetch<T>(
	client: MatrixClient,
	path: string,
	init?: Omit<RequestInit, "headers"> & { headers?: Record<string, string> },
): Promise<T> {
	const token = getAccessTokenOrThrow(client);
	const url = `${client.baseUrl}${path}`;

	const res = await fetch(url, {
		...init,
		headers: {
			Authorization: `Bearer ${token}`,
			...(init?.headers ?? {}),
		},
	});

	if (!res.ok) {
		const text = await res.text().catch(() => "");
		throw new MatrixApiError(`Matrix API error: ${res.status}`, res.status, text);
	}
	return (await res.json()) as T;
}

export type JoinedMembersResponse = {
	joined: Record<string, { display_name?: string; avatar_url?: string }>;
};

export async function getJoinedMembers(
	client: MatrixClient,
	roomId: string,
): Promise<JoinedMembersResponse> {
	return await matrixFetch<JoinedMembersResponse>(
		client,
		`/_matrix/client/v3/rooms/${encodeURIComponent(roomId)}/joined_members`,
	);
}
