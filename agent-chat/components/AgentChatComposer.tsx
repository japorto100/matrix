"use client";

// AC40: auto-resize textarea (grow/shrink with content, max-height scroll)
// AC47: Voice-Input button (Web Speech API, Phase 1 — no model download)
// AC47b: MediaRecorder fallback for Firefox/Safari (no webkitSpeechRecognition)
// AC48b: Mic device selector when MediaRecorder path is active
// AC49: TTS slot exposed via onTriggerSpeech for parent wiring
// AC51c: Paperclip attach button + hidden file input
// AC53: Drag & Drop + Clipboard paste for images

import { Mic, MicOff, Paperclip, RotateCcw, Send, Square } from "lucide-react";
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import type { RequestAttachment, StagedAttachment } from "../hooks/useAttachments";
import { useAttachments } from "../hooks/useAttachments";
import { AttachmentPreviewStrip } from "./AttachmentPreviewStrip";
import { ImagePreviewModal } from "./ImagePreviewModal";

// ---- Web Speech API types ----

interface SpeechRecognitionEvent extends Event {
	results: SpeechRecognitionResultList;
}
interface SpeechRecognitionResultList {
	readonly length: number;
	[index: number]: SpeechRecognitionResult;
}
interface SpeechRecognitionResult {
	readonly length: number;
	[index: number]: SpeechRecognitionAlternative;
	readonly isFinal: boolean;
}
interface SpeechRecognitionAlternative {
	readonly transcript: string;
}
interface SpeechRecognitionInstance extends EventTarget {
	lang: string;
	interimResults: boolean;
	maxAlternatives: number;
	onresult: ((ev: SpeechRecognitionEvent) => void) | null;
	onerror: ((ev: Event) => void) | null;
	onend: (() => void) | null;
	start(): void;
	stop(): void;
	abort(): void;
}
declare global {
	interface Window {
		SpeechRecognition?: new () => SpeechRecognitionInstance;
		webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
	}
}

// ---- Voice state ----

type VoiceState = "inactive" | "listening" | "processing";

function useSpeechInput(onTranscript: (text: string) => void) {
	const [voiceState, setVoiceState] = useState<VoiceState>("inactive");
	const recRef = useRef<SpeechRecognitionInstance | null>(null);

	const isSupported =
		typeof window !== "undefined" &&
		(window.SpeechRecognition !== undefined || window.webkitSpeechRecognition !== undefined);

	const startListening = useCallback(() => {
		if (!isSupported) return;
		const Ctor = window.SpeechRecognition ?? window.webkitSpeechRecognition;
		if (!Ctor) return;
		const rec = new Ctor();
		rec.lang = navigator.language || "en-US";
		rec.interimResults = false;
		rec.maxAlternatives = 1;

		rec.onresult = (ev) => {
			const transcript = ev.results[0]?.[0]?.transcript ?? "";
			if (transcript) {
				setVoiceState("processing");
				onTranscript(transcript);
			}
		};
		rec.onerror = () => setVoiceState("inactive");
		rec.onend = () => setVoiceState("inactive");

		recRef.current = rec;
		rec.start();
		setVoiceState("listening");
	}, [isSupported, onTranscript]);

	const stopListening = useCallback(() => {
		recRef.current?.stop();
		recRef.current = null;
		setVoiceState("inactive");
	}, []);

	const toggleVoice = useCallback(() => {
		if (voiceState === "inactive") startListening();
		else stopListening();
	}, [voiceState, startListening, stopListening]);

	useEffect(
		() => () => {
			recRef.current?.abort();
		},
		[],
	);

	return { voiceState, isSupported, toggleVoice };
}

// ---- AC47b: MediaRecorder fallback (Firefox / Safari without webkitSpeechRecognition) ----

type MediaRecState = "inactive" | "recording" | "processing";

function useMediaRecorderInput(onTranscript: (t: string) => void, deviceId?: string) {
	const [state, setState] = useState<MediaRecState>("inactive");
	const recRef = useRef<MediaRecorder | null>(null);
	const chunksRef = useRef<Blob[]>([]);
	const streamRef = useRef<MediaStream | null>(null);

	const isSupported =
		typeof window !== "undefined" &&
		typeof MediaRecorder !== "undefined" &&
		typeof navigator?.mediaDevices?.getUserMedia === "function";

	const start = useCallback(async () => {
		if (!isSupported) return;
		try {
			const stream = await navigator.mediaDevices.getUserMedia({
				audio: deviceId ? { deviceId: { exact: deviceId } } : true,
			});
			streamRef.current = stream;
			const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
				? "audio/webm;codecs=opus"
				: "audio/webm";
			const recorder = new MediaRecorder(stream, { mimeType });
			chunksRef.current = [];
			recorder.ondataavailable = (e) => {
				if (e.data.size > 0) chunksRef.current.push(e.data);
			};
			recorder.onstop = async () => {
				streamRef.current?.getTracks().forEach((t) => {
					t.stop();
				});
				streamRef.current = null;
				const blob = new Blob(chunksRef.current, { type: mimeType });
				setState("processing");
				try {
					const form = new FormData();
					form.append("file", blob, "recording.webm");
					const res = await fetch("/api/audio/transcribe", { method: "POST", body: form });
					if (res.ok) {
						const data = (await res.json()) as { text?: string };
						if (data.text) onTranscript(data.text);
					}
				} catch {
					// silent fail
				}
				setState("inactive");
			};
			recRef.current = recorder;
			recorder.start();
			setState("recording");
		} catch {
			setState("inactive");
		}
	}, [isSupported, deviceId, onTranscript]);

	const stop = useCallback(() => {
		recRef.current?.stop();
		recRef.current = null;
	}, []);

	const toggle = useCallback(() => {
		if (state === "recording") stop();
		else if (state === "inactive") void start();
	}, [state, start, stop]);

	useEffect(
		() => () => {
			recRef.current?.stop();
			streamRef.current?.getTracks().forEach((t) => {
				t.stop();
			});
		},
		[],
	);

	return { state, isSupported, toggle };
}

// ---- AC48b: Mic device selector ----

function useMicDevices() {
	const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
	const [selectedId, setSelectedId] = useState<string | undefined>();

	useEffect(() => {
		if (typeof navigator?.mediaDevices?.enumerateDevices !== "function") return;
		void navigator.mediaDevices
			.enumerateDevices()
			.then((devs) => {
				const inputs = devs.filter((d) => d.kind === "audioinput");
				setDevices(inputs);
				const def = inputs.find((d) => d.deviceId === "default") ?? inputs[0];
				if (def) setSelectedId(def.deviceId);
			})
			.catch(() => {});
	}, []);

	return { devices, selectedId, setSelectedId };
}

// ---- Composer ----

interface AgentChatComposerProps {
	isStreaming: boolean;
	threadId: string | undefined;
	onSend: (
		text: string,
		attachments?: RequestAttachment[],
		staged?: StagedAttachment[],
	) => Promise<void>;
	onAbort: () => void;
	onRetry?: () => void;
	hasError?: boolean;
	savedInput?: string;
}

export interface AgentChatComposerRef {
	focus: () => void;
}

export const AgentChatComposer = forwardRef<AgentChatComposerRef, AgentChatComposerProps>(
	function AgentChatComposerInner(
		{ isStreaming, threadId, onSend, onAbort, onRetry, hasError, savedInput },
		ref,
	) {
		const [input, setInput] = useState("");
		const textareaRef = useRef<HTMLTextAreaElement>(null);
		const fileInputRef = useRef<HTMLInputElement>(null);
		const pendingRef = useRef(false);
		const [isDragging, setIsDragging] = useState(false);
		const [previewAttachment, setPreviewAttachment] = useState<StagedAttachment | null>(null);

		const {
			attachments,
			addFiles,
			removeAttachment,
			clearAttachments,
			toRequestAttachments,
			hasAttachments,
		} = useAttachments();

		useImperativeHandle(ref, () => ({
			focus: () => setTimeout(() => textareaRef.current?.focus(), 50),
		}));

		const resizeTextarea = useCallback(() => {
			const el = textareaRef.current;
			if (!el) return;
			el.style.height = "auto";
			el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
		}, []);

		const submit = useCallback(async () => {
			const text = input.trim();
			if ((!text && !hasAttachments) || isStreaming || pendingRef.current) return;
			pendingRef.current = true;
			const stagedSnapshot = [...attachments];
			setInput("");
			clearAttachments();
			try {
				const reqAttachments = hasAttachments ? await toRequestAttachments() : undefined;
				await onSend(text || "(image)", reqAttachments, stagedSnapshot);
			} catch {
				setInput(text);
			} finally {
				pendingRef.current = false;
			}
		}, [
			input,
			isStreaming,
			hasAttachments,
			attachments,
			clearAttachments,
			toRequestAttachments,
			onSend,
		]);

		const handleKeyDown = useCallback(
			(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
				if (e.key === "Enter" && !e.shiftKey) {
					e.preventDefault();
					void submit();
				}
			},
			[submit],
		);

		const handleRetry = useCallback(() => {
			if (savedInput) setInput(savedInput);
			onRetry?.();
			setTimeout(() => textareaRef.current?.focus(), 0);
		}, [savedInput, onRetry]);

		// AC47: Speech input — Web Speech API primary, MediaRecorder fallback
		const handleTranscript = useCallback((transcript: string) => {
			setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
			setTimeout(() => textareaRef.current?.focus(), 50);
		}, []);

		const { voiceState, isSupported: wssSupported, toggleVoice } = useSpeechInput(handleTranscript);

		// AC47b: MediaRecorder fallback for Firefox/Safari
		const { devices, selectedId: micDeviceId, setSelectedId: setMicDeviceId } = useMicDevices();
		const {
			state: mediaRecState,
			isSupported: mediaRecSupported,
			toggle: toggleMediaRec,
		} = useMediaRecorderInput(handleTranscript, micDeviceId);

		// Unified mic: prefer Web Speech API, fallback to MediaRecorder
		const hasMic = wssSupported || mediaRecSupported;
		const micActive = wssSupported ? voiceState !== "inactive" : mediaRecState === "recording";
		const micProcessing = wssSupported
			? voiceState === "processing"
			: mediaRecState === "processing";

		const handleMicToggle = useCallback(() => {
			if (wssSupported) toggleVoice();
			else toggleMediaRec();
		}, [wssSupported, toggleVoice, toggleMediaRec]);

		// AC51c: File picker
		const handleFileInputChange = useCallback(
			(e: React.ChangeEvent<HTMLInputElement>) => {
				if (e.target.files) {
					addFiles(e.target.files);
					e.target.value = "";
				}
			},
			[addFiles],
		);

		// AC53: Drag & Drop
		const handleDragOver = useCallback((e: React.DragEvent) => {
			e.preventDefault();
			setIsDragging(true);
		}, []);

		const handleDragLeave = useCallback((e: React.DragEvent) => {
			e.preventDefault();
			setIsDragging(false);
		}, []);

		const handleDrop = useCallback(
			(e: React.DragEvent) => {
				e.preventDefault();
				setIsDragging(false);
				const files = Array.from(e.dataTransfer.files);
				if (files.length) addFiles(files);
			},
			[addFiles],
		);

		// AC53: Clipboard paste
		const handlePaste = useCallback(
			(e: React.ClipboardEvent<HTMLTextAreaElement>) => {
				const items = Array.from(e.clipboardData.items);
				const imageFiles = items
					.filter((item) => item.kind === "file" && item.type.startsWith("image/"))
					.map((item) => item.getAsFile())
					.filter((f): f is File => f !== null);
				if (imageFiles.length) {
					e.preventDefault();
					addFiles(imageFiles);
				}
			},
			[addFiles],
		);

		return (
			<div
				className={`border-t border-border px-3 py-2 space-y-1.5 transition-colors ${
					isDragging ? "bg-primary/5 border-primary/40" : ""
				}`}
				onDragOver={handleDragOver}
				onDragLeave={handleDragLeave}
				onDrop={handleDrop}
			>
				{hasError && onRetry && (
					<div className="flex justify-end">
						<Button
							variant="ghost"
							size="sm"
							className="h-6 gap-1 px-2 text-[10px] text-destructive hover:text-destructive"
							onClick={handleRetry}
						>
							<RotateCcw className="h-3 w-3" />
							Retry last message
						</Button>
					</div>
				)}

				{/* AC52: Attachment preview strip */}
				<AttachmentPreviewStrip
					attachments={attachments}
					onRemove={removeAttachment}
					onPreview={setPreviewAttachment}
				/>

				<div className="flex items-end gap-2">
					{/* AC47/AC47b: Mic — Web Speech primary, MediaRecorder fallback */}
					{hasMic && (
						<div className="flex items-center gap-0.5 shrink-0">
							<Button
								type="button"
								variant="ghost"
								size="icon"
								className={`h-9 w-9 transition-colors ${
									micActive
										? "text-red-500 hover:text-red-400 bg-red-500/10"
										: "text-muted-foreground hover:text-foreground"
								}`}
								onClick={handleMicToggle}
								disabled={isStreaming || micProcessing}
								title={micActive ? "Stop recording" : "Voice input"}
							>
								{micActive ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
							</Button>
							{/* AC48b: Device selector — only when MediaRecorder path + multiple devices */}
							{!wssSupported && devices.length > 1 && (
								<select
									value={micDeviceId ?? ""}
									onChange={(e) => setMicDeviceId(e.target.value)}
									className="max-w-[80px] truncate rounded border border-border bg-background px-1 py-0.5 text-[10px] text-muted-foreground focus:outline-none"
									title="Select microphone"
								>
									{devices.map((d) => (
										<option key={d.deviceId} value={d.deviceId}>
											{d.label || `Mic ${d.deviceId.slice(0, 6)}`}
										</option>
									))}
								</select>
							)}
						</div>
					)}

					{/* AC51: Paperclip button + staged count badge */}
					<Button
						type="button"
						variant="ghost"
						size="icon"
						className="relative h-9 w-9 shrink-0 text-muted-foreground hover:text-foreground"
						onClick={() => fileInputRef.current?.click()}
						disabled={isStreaming}
						title="Attach image"
					>
						<Paperclip className="h-4 w-4" />
						{attachments.length > 0 && (
							<span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[9px] font-bold text-primary-foreground tabular-nums">
								{attachments.length}
							</span>
						)}
					</Button>
					<input
						ref={fileInputRef}
						type="file"
						accept="image/jpeg,image/png,image/gif,image/webp"
						multiple
						className="hidden"
						onChange={handleFileInputChange}
					/>

					{/* AC40: auto-resize textarea */}
					<textarea
						ref={textareaRef}
						value={input}
						onChange={(e) => {
							setInput(e.target.value);
							resizeTextarea();
						}}
						onKeyDown={handleKeyDown}
						onPaste={handlePaste}
						placeholder={
							micActive
								? "Listening…"
								: isDragging
									? "Drop image here…"
									: isStreaming
										? "Responding…"
										: "Message agent… (Enter to send)"
						}
						disabled={isStreaming}
						rows={1}
						className="flex-1 min-h-[36px] max-h-[160px] resize-none rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 overflow-y-auto"
					/>

					{isStreaming ? (
						<Button
							variant="outline"
							size="icon"
							className="h-9 w-9 shrink-0 text-destructive hover:text-destructive"
							onClick={onAbort}
							title="Stop generation"
						>
							<Square className="h-3.5 w-3.5" />
						</Button>
					) : (
						<Button
							size="icon"
							className="h-9 w-9 shrink-0"
							onClick={() => void submit()}
							disabled={!input.trim() && !hasAttachments}
							title="Send (Enter)"
						>
							<Send className="h-3.5 w-3.5" />
						</Button>
					)}
				</div>

				<div className="flex items-center justify-between">
					<span className="text-[9px] text-muted-foreground/50">
						read-only · bounded-write via BFF/Gateway
						{micActive && <span className="ml-2 text-red-400 animate-pulse">● recording</span>}
						{micProcessing && <span className="ml-2 text-amber-400">processing…</span>}
					</span>
					{threadId && (
						<span className="text-[9px] font-mono text-muted-foreground/40 truncate max-w-[130px]">
							{threadId}
						</span>
					)}
				</div>

				{/* AC55: Image preview modal */}
				<ImagePreviewModal
					attachment={previewAttachment}
					onClose={() => setPreviewAttachment(null)}
				/>
			</div>
		);
	},
);
