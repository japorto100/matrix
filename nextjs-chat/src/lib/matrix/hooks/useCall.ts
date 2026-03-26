"use client";

import { CallEvent, createNewMatrixCall, type MatrixCall } from "matrix-js-sdk";
import { CallState } from "matrix-js-sdk/lib/webrtc/call";
import { CallEventHandlerEvent } from "matrix-js-sdk/lib/webrtc/callEventHandler";
import { useCallback, useEffect, useRef, useState } from "react";
import { useMatrixClient } from "./useMatrixClient";

export type CallStatus = "idle" | "incoming" | "outgoing" | "connecting" | "connected" | "ended";

export interface UseCallReturn {
	callStatus: CallStatus;
	activeCall: MatrixCall | null;
	callerName: string | null;
	placeCall: (roomId: string, withVideo?: boolean) => Promise<void>;
	answerCall: () => Promise<void>;
	rejectCall: () => void;
	hangupCall: () => void;
	toggleMute: () => Promise<void>;
	toggleCamera: () => Promise<void>;
	isMuted: boolean;
	isCameraOff: boolean;
	localVideoRef: React.RefObject<HTMLVideoElement | null>;
	remoteVideoRef: React.RefObject<HTMLVideoElement | null>;
}

export function useCall(): UseCallReturn {
	const { client } = useMatrixClient();
	const [callStatus, setCallStatus] = useState<CallStatus>("idle");
	const [activeCall, setActiveCall] = useState<MatrixCall | null>(null);
	const [callerName, setCallerName] = useState<string | null>(null);
	const [isMuted, setIsMuted] = useState(false);
	const [isCameraOff, setIsCameraOff] = useState(false);
	const localVideoRef = useRef<HTMLVideoElement | null>(null);
	const remoteVideoRef = useRef<HTMLVideoElement | null>(null);

	// B-9 Fix: Ref für activeCall Guard im Incoming-Listener (kein stale closure)
	const activeCallRef = useRef<MatrixCall | null>(null);
	activeCallRef.current = activeCall;

	// Call-Zustand auf SDK-State mappen
	const bindCallEvents = useCallback((call: MatrixCall) => {
		call.on(CallEvent.State, (state: CallState) => {
			switch (state) {
				case CallState.Ringing:
					setCallStatus("incoming");
					break;
				case CallState.InviteSent:
				case CallState.WaitLocalMedia:
				case CallState.CreateOffer:
				case CallState.CreateAnswer:
					setCallStatus("outgoing");
					break;
				case CallState.Connecting:
					setCallStatus("connecting");
					break;
				case CallState.Connected:
					setCallStatus("connected");
					break;
				case CallState.Ended:
					setCallStatus("ended");
					setTimeout(() => {
						setCallStatus("idle");
						setActiveCall(null);
						setCallerName(null);
					}, 1500);
					break;
			}
		});

		call.on(CallEvent.FeedsChanged, () => {
			const local = call.getLocalFeeds()[0]?.stream;
			const remote = call.getRemoteFeeds()[0]?.stream;
			if (localVideoRef.current && local) localVideoRef.current.srcObject = local;
			if (remoteVideoRef.current && remote) remoteVideoRef.current.srcObject = remote;
		});
	}, []);

	// B-9 Fix: Eingehende Calls abfangen — Ref statt State in Deps
	useEffect(() => {
		if (!client) return;

		function onIncoming(call: MatrixCall) {
			// Laufenden Call nicht überschreiben (Ref statt stale closure)
			if (activeCallRef.current) {
				call.reject();
				return;
			}
			const caller =
				client?.getUser(call.getOpponentMember()?.userId ?? "")?.displayName ??
				call.getOpponentMember()?.userId ??
				"Unbekannt";
			setCallerName(caller);
			setActiveCall(call);
			setCallStatus("incoming");
			bindCallEvents(call);
		}

		client.on(CallEventHandlerEvent.Incoming, onIncoming);
		return () => {
			client.off(CallEventHandlerEvent.Incoming, onIncoming);
		};
	}, [client, bindCallEvents]); // activeCall entfernt → kein Re-Register bei Call-State-Change

	const placeCall = useCallback(
		async (roomId: string, withVideo = false) => {
			if (!client) return;
			const call = createNewMatrixCall(client, roomId);
			if (!call) return;
			setActiveCall(call);
			// B-9 Fix: Status sofort setzen bevor async SDK call
			setCallStatus("outgoing");
			// B-9 Fix: callerName für ausgehende Calls setzen
			const room = client.getRoom(roomId);
			if (room) {
				const myId = client.getUserId();
				const members = room.getJoinedMembers();
				const other = members.find((m) => m.userId !== myId);
				setCallerName(other?.name ?? other?.userId ?? null);
			}
			bindCallEvents(call);
			if (withVideo) {
				await call.placeVideoCall();
			} else {
				await call.placeVoiceCall();
			}
		},
		[client, bindCallEvents],
	);

	const answerCall = useCallback(async () => {
		if (!activeCall) return;
		await activeCall.answer();
	}, [activeCall]);

	const rejectCall = useCallback(() => {
		if (!activeCall) return;
		activeCall.reject();
		setCallStatus("idle");
		setActiveCall(null);
	}, [activeCall]);

	const hangupCall = useCallback(() => {
		if (!activeCall) return;
		// biome-ignore lint/suspicious/noExplicitAny: hangup erwartet CallErrorCode, 'user_hangup' ist valide
		activeCall.hangup("user_hangup" as any, false);
	}, [activeCall]);

	const toggleMute = useCallback(async () => {
		if (!activeCall) return;
		const next = !isMuted;
		await activeCall.setMicrophoneMuted(next);
		setIsMuted(next);
	}, [activeCall, isMuted]);

	const toggleCamera = useCallback(async () => {
		if (!activeCall) return;
		const next = !isCameraOff;
		await activeCall.setLocalVideoMuted(next);
		setIsCameraOff(next);
	}, [activeCall, isCameraOff]);

	return {
		callStatus,
		activeCall,
		callerName,
		placeCall,
		answerCall,
		rejectCall,
		hangupCall,
		toggleMute,
		toggleCamera,
		isMuted,
		isCameraOff,
		localVideoRef,
		remoteVideoRef,
	};
}
