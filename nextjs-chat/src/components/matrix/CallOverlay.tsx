"use client";

import {
	AudioConference,
	LiveKitRoom,
	RoomAudioRenderer,
	VideoConference,
} from "@livekit/components-react";
import "@livekit/components-styles";
import { BackgroundBlur, type BackgroundOptions } from "@livekit/track-processors";
import type { RoomOptions } from "livekit-client";
import { PhoneOff, ShieldCheck } from "lucide-react";
import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import type { UseMatrixRTCCallReturn } from "@/lib/matrix/hooks/useMatrixRTCCall";

interface Props {
	call: UseMatrixRTCCallReturn;
}

/**
 * Call-Overlay — LiveKit-basiertes Video/Audio UI mit E2EE.
 * Nutzt @livekit/components-react Prefabs für Grid, Controls, Screen Share.
 * E2EE Keys werden von MatrixKeyProvider (matrix-js-sdk → LiveKit) gespeist.
 */
export function CallOverlay({ call }: Props) {
	const {
		callStatus,
		livekitToken,
		livekitUrl,
		leaveCall,
		participantCount,
		e2eeKeyProvider,
		isVoiceOnly,
	} = call;

	// LiveKit RoomOptions: E2EE + Video Processors (Background Blur)
	const roomOptions = useMemo((): RoomOptions | undefined => {
		if (typeof window === "undefined") return undefined;

		const options: RoomOptions = {};

		// E2EE — Worker verschlüsselt Audio/Video Frames (SFrame)
		try {
			const worker = new Worker(new URL("livekit-client/e2ee-worker", import.meta.url));
			options.e2ee = { keyProvider: e2eeKeyProvider, worker };
		} catch {
			console.warn("[call] E2EE Worker nicht verfügbar — Calls laufen unverschlüsselt");
		}

		// Background Blur für Video-Calls (track-processors)
		try {
			options.videoCaptureDefaults = {
				processor: BackgroundBlur(10),
			};
		} catch {
			// Track Processors nicht verfügbar — kein Blur
		}

		return options;
	}, [e2eeKeyProvider]);

	const isE2EE = !!roomOptions?.e2ee;

	if (callStatus === "idle" || !livekitToken || !livekitUrl) return null;

	if (callStatus === "joining") {
		return (
			<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
				<div className="bg-card rounded-2xl shadow-2xl p-8 text-center">
					<div className="h-12 w-12 mx-auto mb-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
					<p className="text-lg font-semibold">Verbinde...</p>
					<p className="text-sm text-muted-foreground mt-1">MatrixRTC Session wird aufgebaut</p>
				</div>
			</div>
		);
	}

	return (
		<div className="fixed inset-0 z-50 bg-black">
			<LiveKitRoom
				token={livekitToken}
				serverUrl={livekitUrl}
				connect={true}
				video={!isVoiceOnly}
				onDisconnected={() => leaveCall()}
				options={roomOptions}
				className="h-full w-full"
			>
				{/* Voice-only → kompaktes Audio UI, Video → volles Grid mit Screen Share */}
				{isVoiceOnly ? <AudioConference /> : <VideoConference />}
				<RoomAudioRenderer />

				{/* Status-Bar: E2EE Badge + Teilnehmer + Hangup */}
				<div className="absolute bottom-4 right-4 z-10 flex items-center gap-2">
					{isE2EE && (
						<span className="flex items-center gap-1 text-xs text-green-400 bg-black/40 px-2 py-1 rounded">
							<ShieldCheck className="h-3 w-3" />
							E2EE
						</span>
					)}
					<span className="text-xs text-white/60 bg-black/40 px-2 py-1 rounded">
						{participantCount} Teilnehmer
					</span>
					<Button
						variant="destructive"
						size="icon"
						className="h-12 w-12 rounded-full shadow-lg"
						onClick={() => leaveCall()}
						title="Auflegen"
					>
						<PhoneOff className="h-5 w-5" />
					</Button>
				</div>
			</LiveKitRoom>
		</div>
	);
}
