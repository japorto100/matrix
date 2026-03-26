"use client";

import { Mic, MicOff, Phone, PhoneOff, Video, VideoOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { UseCallReturn } from "@/lib/matrix/hooks/useCall";
import { cn } from "@/lib/utils";

interface Props {
	call: UseCallReturn;
}

/**
 * B-9: Call-Overlay — Klingeln + aktiver Call (Picture-in-Picture Stil).
 * Wird über dem Chat-Bereich gerendert wenn ein Call aktiv ist.
 */
export function CallOverlay({ call }: Props) {
	const {
		callStatus,
		callerName,
		answerCall,
		rejectCall,
		hangupCall,
		toggleMute,
		toggleCamera,
		isMuted,
		isCameraOff,
		localVideoRef,
		remoteVideoRef,
	} = call;

	if (callStatus === "idle") return null;

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
			<div className="relative bg-card rounded-2xl shadow-2xl overflow-hidden w-[480px] max-w-[95vw]">
				{/* Remote Video (groß) */}
				<div className="relative bg-zinc-900 aspect-video w-full flex items-center justify-center">
					{/* biome-ignore lint/a11y/useMediaCaption: Call-Video hat keine Captions */}
					<video
						ref={remoteVideoRef}
						autoPlay
						playsInline
						className={cn("w-full h-full object-cover", callStatus !== "connected" && "hidden")}
					/>

					{/* Status-Text wenn nicht verbunden */}
					{callStatus !== "connected" && (
						<div className="flex flex-col items-center gap-3 text-white">
							<div className="h-20 w-20 rounded-full bg-primary/30 flex items-center justify-center text-3xl font-bold">
								{callerName?.slice(0, 2).toUpperCase() ?? "??"}
							</div>
							<p className="text-lg font-semibold">{callerName ?? "Unbekannt"}</p>
							<p className="text-sm text-white/70">
								{callStatus === "incoming" && "Eingehender Anruf…"}
								{callStatus === "outgoing" && "Wählt…"}
								{callStatus === "connecting" && "Verbinde…"}
								{callStatus === "ended" && "Anruf beendet"}
							</p>
						</div>
					)}

					{/* Lokales Video (klein, oben rechts) */}
					{/* biome-ignore lint/a11y/useMediaCaption: eigenes Preview-Video */}
					<video
						ref={localVideoRef}
						autoPlay
						playsInline
						muted
						className="absolute top-3 right-3 w-28 rounded-lg shadow-lg object-cover aspect-video bg-zinc-800"
					/>
				</div>

				{/* Steuerleiste */}
				<div className="flex items-center justify-center gap-3 p-4 bg-card">
					{/* Eingehend: Annehmen / Ablehnen */}
					{callStatus === "incoming" && (
						<>
							<Button
								size="icon"
								className="h-12 w-12 rounded-full bg-green-600 hover:bg-green-700"
								onClick={answerCall}
								title="Annehmen"
							>
								<Phone className="h-5 w-5" />
							</Button>
							<Button
								size="icon"
								variant="destructive"
								className="h-12 w-12 rounded-full"
								onClick={rejectCall}
								title="Ablehnen"
							>
								<PhoneOff className="h-5 w-5" />
							</Button>
						</>
					)}

					{/* Aktiver Call: Mute / Kamera / Auflegen */}
					{(callStatus === "outgoing" ||
						callStatus === "connecting" ||
						callStatus === "connected") && (
						<>
							<Button
								size="icon"
								variant={isMuted ? "destructive" : "secondary"}
								className="h-10 w-10 rounded-full"
								onClick={toggleMute}
								title={isMuted ? "Stummschaltung aufheben" : "Stummschalten"}
							>
								{isMuted ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
							</Button>
							<Button
								size="icon"
								variant={isCameraOff ? "destructive" : "secondary"}
								className="h-10 w-10 rounded-full"
								onClick={toggleCamera}
								title={isCameraOff ? "Kamera einschalten" : "Kamera ausschalten"}
							>
								{isCameraOff ? <VideoOff className="h-4 w-4" /> : <Video className="h-4 w-4" />}
							</Button>
							<Button
								size="icon"
								variant="destructive"
								className="h-12 w-12 rounded-full"
								onClick={hangupCall}
								title="Auflegen"
							>
								<PhoneOff className="h-5 w-5" />
							</Button>
						</>
					)}

					{/* Beendet */}
					{callStatus === "ended" && (
						<p className="text-sm text-muted-foreground py-2">Anruf beendet</p>
					)}
				</div>
			</div>
		</div>
	);
}
