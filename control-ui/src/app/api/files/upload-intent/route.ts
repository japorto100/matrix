// POST /api/files/upload-intent — request a presigned upload URL from Go
// bounded-write: audit fields required (DW18).
// Go Gateway signs the S3/R2 presigned URL; browser uploads directly to object store.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { writeFileAudit } from "@/lib/server/file-audit";
import { getErrorMessage } from "@/lib/utils";

const GATEWAY_BASE = process.env.GATEWAY_URL ?? "http://localhost:9060";

interface UploadIntentBody {
	filename: string;
	content_type: string;
	size_bytes: number;
}

export async function POST(request: NextRequest) {
	const requestId = request.headers.get("x-request-id") ?? crypto.randomUUID();
	const actorUserId = request.headers.get("x-actor-user-id") ?? undefined;
	const actorRole = request.headers.get("x-actor-role") ?? undefined;

	let body: UploadIntentBody;
	try {
		body = (await request.json()) as UploadIntentBody;
	} catch {
		return NextResponse.json(
			{ code: "INVALID_REQUEST", requestId },
			{ status: 400, headers: { "x-request-id": requestId } },
		);
	}

	if (!body.filename || !body.content_type || typeof body.size_bytes !== "number") {
		return NextResponse.json(
			{
				code: "INVALID_REQUEST",
				message: "filename, content_type, size_bytes required",
				requestId,
			},
			{ status: 400, headers: { "x-request-id": requestId } },
		);
	}

	try {
		const upstream = await fetch(`${GATEWAY_BASE}/api/v1/files/upload-intent`, {
			method: "POST",
			headers: {
				"content-type": "application/json",
				"x-request-id": requestId,
			},
			body: JSON.stringify(body),
			cache: "no-store",
		});

		if (!upstream.ok) {
			const err = (await upstream.json().catch(() => ({}))) as Record<string, unknown>;
			return NextResponse.json(
				{ code: (err.code as string) ?? "STORAGE_UNAVAILABLE", requestId },
				{ status: upstream.status, headers: { "x-request-id": requestId } },
			);
		}

		const data = (await upstream.json()) as { file_id?: string };

		// Audit: upload intent granted (bounded-write)
		await writeFileAudit({
			action: "upload",
			actionClass: "bounded-write",
			requestId,
			target: body.filename,
			actorUserId,
			actorRole,
			status: "ok",
		});

		return NextResponse.json(data, {
			status: 201,
			headers: {
				"cache-control": "no-store",
				"x-request-id": requestId,
			},
		});
	} catch (error: unknown) {
		return NextResponse.json(
			{ code: "STORAGE_UNAVAILABLE", message: getErrorMessage(error), requestId },
			{ status: 503, headers: { "x-request-id": requestId } },
		);
	}
}
