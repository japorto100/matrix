"use client";

/**
 * MatrixRTC Call Hook — LiveKit-basierte Calls über matrix-js-sdk MatrixRTCSession.
 *
 * Ersetzt den legacy useCall.ts (createNewMatrixCall, deprecated MSC2746).
 * Nutzt LiveKit SFU für Audio/Video und matrix-js-sdk's eingebautes MatrixRTC-Modul
 * für Session-Management (m.rtc.member State Events).
 *
 * E2EE: matrix-js-sdk generiert Media Keys → MatrixKeyProvider → LiveKit SFrame Encryption.
 *
 * Backend: LiveKit SFU (Port 7880) + lk-jwt-service (Port 8080)
 */

import type { MatrixClient } from "matrix-js-sdk";
import {
	type LivekitTransportConfig,
	type MatrixRTCSession,
	MatrixRTCSessionEvent,
} from "matrix-js-sdk/lib/matrixrtc";
import type { CallMembershipIdentityParts } from "matrix-js-sdk/lib/matrixrtc/EncryptionManager";
import { useCallback, useEffect, useRef, useState } from "react";
import { MatrixKeyProvider, makeParticipantIdentity } from "../MatrixKeyProvider";

export type RTCCallStatus = "idle" | "joining" | "connected" | "leaving";

export interface UseMatrixRTCCallReturn {
	callStatus: RTCCallStatus;
	/** LiveKit JWT Token (für <LiveKitRoom token={...}>) */
	livekitToken: string | null;
	/** LiveKit Server URL (für <LiveKitRoom serverUrl={...}>) */
	livekitUrl: string | null;
	/** Anzahl aktiver Teilnehmer im Call */
	participantCount: number;
	/** E2EE KeyProvider für LiveKit Room */
	e2eeKeyProvider: MatrixKeyProvider;
	/** Ob der aktuelle Call Audio-only ist */
	isVoiceOnly: boolean;
	/** Call starten oder beitreten */
	joinCall: (roomId: string, intent?: "m.voice" | "m.video") => Promise<void>;
	/** Call verlassen */
	leaveCall: () => Promise<void>;
}

/** Env fallback for lk-jwt-service URL (Dev: localhost, Prod: hinter Reverse Proxy) */
const LK_JWT_ENV_URL = process.env.NEXT_PUBLIC_LK_JWT_SERVICE_URL ?? "http://localhost:8080";

/**
 * Holt ein LiveKit JWT vom lk-jwt-service.
 * URL-Aufloesung: SDK getLivekitServiceURL() (aus .well-known) → Env-Fallback.
 * Der Service validiert das Matrix OpenID Token und gibt ein LiveKit JWT zurueck.
 */
async function fetchLivekitToken(
	client: MatrixClient,
	roomId: string,
): Promise<{ token: string; url: string }> {
	const serviceUrl = client.getLivekitServiceURL() ?? LK_JWT_ENV_URL;
	const openIdToken = await client.getOpenIdToken();
	const res = await fetch(`${serviceUrl}/sfu/get`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({
			room: roomId,
			openid_token: openIdToken,
			device_id: client.getDeviceId(),
		}),
	});

	if (!res.ok) {
		throw new Error(`lk-jwt-service error: ${res.status} ${await res.text()}`);
	}

	const data = (await res.json()) as { jwt: string; url: string };
	return { token: data.jwt, url: data.url };
}

export function useMatrixRTCCall(client: MatrixClient | null): UseMatrixRTCCallReturn {
	const [callStatus, setCallStatus] = useState<RTCCallStatus>("idle");
	const [livekitToken, setLivekitToken] = useState<string | null>(null);
	const [livekitUrl, setLivekitUrl] = useState<string | null>(null);
	const [participantCount, setParticipantCount] = useState(0);
	const [isVoiceOnly, setIsVoiceOnly] = useState(false);
	const sessionRef = useRef<MatrixRTCSession | null>(null);
	const keyProviderRef = useRef(new MatrixKeyProvider());

	const onMembershipsChanged = useCallback(() => {
		const session = sessionRef.current;
		if (session) {
			setParticipantCount(session.memberships.length);
		}
	}, []);

	// E2EE: Keys von MatrixRTC → LiveKit KeyProvider
	const onEncryptionKeyChanged = useCallback(
		(
			key: Uint8Array,
			keyIndex: number,
			membership: CallMembershipIdentityParts,
			_rtcBackendIdentity: string,
		) => {
			const identity = makeParticipantIdentity(membership.userId, membership.deviceId);
			keyProviderRef.current.setEncryptionKey(key, keyIndex, identity).catch((err) => {
				console.error("[matrixrtc] Failed to set encryption key:", err);
			});
		},
		[],
	);

	const joinCall = useCallback(
		async (roomId: string, intent: "m.voice" | "m.video" = "m.video") => {
			if (!client || callStatus !== "idle") return;

			const room = client.getRoom(roomId);
			if (!room) throw new Error(`Room ${roomId} not found`);

			setCallStatus("joining");
			setIsVoiceOnly(intent === "m.voice");

			try {
				const session = client.matrixRTC.getRoomSession(room);
				sessionRef.current = session;

				const { token, url } = await fetchLivekitToken(client, roomId);
				setLivekitToken(token);
				setLivekitUrl(url);

				const livekitFocus: LivekitTransportConfig = {
					type: "livekit",
					livekit_service_url: client.getLivekitServiceURL() ?? LK_JWT_ENV_URL,
				};

				// E2EE aktiviert: matrix-js-sdk generiert + verteilt Media Keys
				session.joinRoomSession([livekitFocus], undefined, {
					callIntent: intent === "m.voice" ? "m.voice" : "m.video",
					manageMediaKeys: true,
				});

				session.on(MatrixRTCSessionEvent.MembershipsChanged, onMembershipsChanged);
				session.on(MatrixRTCSessionEvent.EncryptionKeyChanged, onEncryptionKeyChanged);

				// Bestehende Keys exportieren (für Teilnehmer die vor uns da waren)
				session.reemitEncryptionKeys();

				setParticipantCount(session.memberships.length);
				setCallStatus("connected");
			} catch (err) {
				console.error("[matrixrtc] join failed:", err);
				setCallStatus("idle");
				setLivekitToken(null);
				setLivekitUrl(null);
				throw err;
			}
		},
		[client, callStatus, onMembershipsChanged, onEncryptionKeyChanged],
	);

	const leaveCall = useCallback(async () => {
		const session = sessionRef.current;
		if (!session) return;

		setCallStatus("leaving");
		session.off(MatrixRTCSessionEvent.MembershipsChanged, onMembershipsChanged);
		session.off(MatrixRTCSessionEvent.EncryptionKeyChanged, onEncryptionKeyChanged);

		try {
			await session.leaveRoomSession(5000);
		} catch (err) {
			console.error("[matrixrtc] leave failed:", err);
		} finally {
			sessionRef.current = null;
			setLivekitToken(null);
			setLivekitUrl(null);
			setParticipantCount(0);
			setIsVoiceOnly(false);
			setCallStatus("idle");
		}
	}, [onMembershipsChanged, onEncryptionKeyChanged]);

	useEffect(() => {
		return () => {
			const session = sessionRef.current;
			if (session) {
				session.off(MatrixRTCSessionEvent.MembershipsChanged, onMembershipsChanged);
				session.off(MatrixRTCSessionEvent.EncryptionKeyChanged, onEncryptionKeyChanged);
				session.leaveRoomSession(2000).catch(() => {});
				sessionRef.current = null;
			}
		};
	}, [onMembershipsChanged, onEncryptionKeyChanged]);

	return {
		callStatus,
		livekitToken,
		livekitUrl,
		participantCount,
		e2eeKeyProvider: keyProviderRef.current,
		isVoiceOnly,
		joinCall,
		leaveCall,
	};
}
