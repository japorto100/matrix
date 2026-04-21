# Agent Chat UI Delta

> **Stand:** 23. Maerz 2026 (Rev. 31)
> **Phase:** 22a — Agent Chat UI + Streaming Frontend
> **Zweck:** Execution-Owner fuer den Chat-UI-Layer ueber dem Go/Python Agent-Stack.
> **Aenderungshistorie:**
> - Rev. 1–8 (12.–13.03.2026): Scaffold, SDK-Eval, Normalisierung, Mission-Control/Onyx/Deepdive-Hardening
> - Rev. 9 (13.03.2026): Phase-A-Implementierung eingetragen; erledigte ACs markiert
> - Rev. 10 (14.03.2026): Vollstaendiger Feature-Gap aus Clone-Analyse (AgentZero/Perplexica/Onyx) aufgenommen; SOTA-2026-Block neu; alle ACs und Verify-Gates aktualisiert
> - Rev. 11 (14.03.2026): Phase-B-Implementierung — H/N/I-partial/J-partial abgearbeitet; AC34-40, AC41, AC47, AC49, AC61, AC62 done; tsc 0 Fehler, Biome 0 Fehler
> - Rev. 12 (14.03.2026): Phase-C — AC49, AC70, AC71, AC72 implementiert; TTS + EventRail + ReconnectBanner + Toolbar; tsc 0, Biome 0
> - Rev. 13 (14.03.2026): SDK-Entscheid dokumentiert (Sektion Q); App-Struktur-Aenderung `(shell)/` Route Group festgehalten; Global-Overlay-Architektur in command_keyboard_delta.md verlinkt
> - Rev. 14 (14.03.2026): Phase-D — AC46/AC67/AC68 implementiert; Paced Turn Groups (framer-motion), React.memo (Message/ToolBlock/Markdown), focus-Management via forwardRef; tsc 0, Biome 0
> - Rev. 15 (14.03.2026): Sektion S — SOTA 2026 Contextual AI Entry Points aufgenommen (AC87-AC97, Verify-Gates AC.V41-V47); GlobalTopBar 3-Layer-Architektur festgelegt
> - Rev. 16 (16.03.2026): Frontend-Chat-Contract synchronisiert (`stop` xor `resume`, metadata/data-parts, approval continuation, cleanup/idempotenz); Vercel-SDK-Sektion auf "pausiert nach Analyse" gesetzt; AC73 in `stop_generation`/`resume_stream`/`pause_loop_resume_loop` gesplittet
> - Rev. 17 (17.03.2026): Phase-22c abgeschlossen — AC74/AC75/AC76/AC77 done; `CommandPalette` → `src/components/CommandPalette.tsx` (global, `useGlobalChat()` intern); `GlobalChatProvider`+`GlobalKeyboardProvider`+`GlobalChatOverlay` in `(shell)/layout.tsx`; Bot-Icon in `GlobalTopBar`; AC87 done — `buildTradingContext()` + `setChatContext` Injection in trading/page.tsx; AC91/AC92 Evaluation abgeschlossen; Sektion S AC95 ergaenzt; DocumentViewer TS-Fehler behoben (`renderError` statt `onDocumentLoadFailure`); tsc 0 Fehler, Biome 0 Fehler
> - Rev. 18 (17.03.2026): AC88/AC89/AC94 implementiert — Context-Chip in `AgentChatHeader` (dismissible, emerald Badge); proaktiver Badge am Bot-Icon (`badgeCount` in GlobalChatContext, Puls-Animation); Split-View Toggle (`ChatMode` sheet/split, `SplitChatShell.tsx`, Toggle-Button in AgentChatToolbar); `incrementBadge`/`clearBadge`/`toggleMode` in GlobalChatContext; tsc 0 neue Fehler, Biome 0 Fehler
> - Rev. 19 (17.03.2026): Verify-Gates ergaenzt — AC41/AC46/AC67/AC68/AC70/AC71 hatten keine Gates; AC.V59-V63 hinzugefuegt
> - Rev. 20 (17.03.2026): Phase 22d abgeschlossen — AC78/AC80/AC81/AC82/AC83/AC84/AC85/AC86 done; `ai@6.0.116` + `@ai-sdk/react@3.0.118` installiert; `useChatSession.ts` auf `useChat` + `DefaultChatTransport` + `prepareSendMessagesRequest` umgebaut; BFF auf UIMessage-Stream-Protokoll umgestellt (`x-vercel-ai-ui-message-stream: v1` + `error`→`errorText` Rewrite); `AgentChatMessage.tsx` auf `UIMessage`-Parts (text/reasoning/dynamic-tool); `AgentChatToolBlock.tsx` auf `DynamicToolUIPart` (7 States); `types.ts` bereinigt (ChatBlock/SseEvent entfernt); AC79 (Go Protocol Header) in `agent_chat_runtime_delta.md` impl-owned (done)
> - Rev. 23 (17.03.2026): Frontend-Batch — AC47b/AC48b/AC50/AC63/AC105 done; MediaRecorder-Fallback+MicSelector in AgentChatComposer; TTS-Autoplay Toggle (Toolbar+Thread); JSON-Structured-Output-Renderer in AgentChatMarkdown; Message-Branching (Edit+Resend) in AgentChatMessage+useChatSession; Biome 0 Fehler 3 Warnings (noImgElement, blob://, intentional)
> - Rev. 29 (17.03.2026): Verify-Gates Phase 22f/22g ergaenzt (AC.V77-AC.V86); AC.V25 korrigiert (STT/TTS jetzt via BFF, nicht mehr browser-only); pre-existing tsc-Fehler als behoben markiert (AC.V85/AC.V86)
> - Rev. 31 (23.03.2026): Live-Verify Session — NuqsAdapter in providers.tsx verifiziert (kein NUQS-404 mehr); Chat-Overlay oeffnet via Klick + ⌘L verifiziert; ⌘K CommandPalette verifiziert; AC.V32/AC.V33 auf [x] gesetzt; AC.V35 (⌘T) noch offen (nicht getestet); ⌘A Audio = command_keyboard_delta scope
> - Rev. 30 (18.03.2026): AC6/AC7 als code-complete markiert (Phase 22g Loop-Neubau); Backend-Sektion aktualisiert
> - Rev. 28 (17.03.2026): AC51/AC109 done — Paperclip Count-Badge (relative+absolute, primary color, tabular-nums); AC109 Structured-Output+Thinking-Inkompatibilitaet generisch dokumentiert (provider-agnostisch, 3 Workaround-Strategien); AC45 als Backlog/Skip fuer Trading-App bewertet
> - Rev. 27 (17.03.2026): AC66/AC57/AC58 done — Tool-Approval-Chain vollstaendig verdrahtet (useChatSession→AgentChatPanel→AgentChatThread→AgentChatMessage→AgentChatToolBlock, BFF approve route); AgentChatSources.tsx NEU (extractSources Annotations+Data-Parts, Inline-Cards+Dialog-Overflow, Count-Badge); AC100/AC102 als DEFERRED markiert
> - Rev. 26 (17.03.2026): AC42/AC43/AC44 done — Regenerate-Button (RotateCcw, letzter Assistant-Message-Footer, ruft retry()); Feedback-Buttons (ThumbsUp/ThumbsDown, lokaler Toggle-State, kein Backend); AC43 als AC105-Alias markiert; memo-Comparator isLast ergaenzt; Biome 0 Fehler
> - Rev. 25 (17.03.2026): AC95 done — IndicatorAiTooltip NEU (useCompletion, HoverCard 600ms); /api/agent/completion NEU (Go-Gateway-Proxy, kein @ai-sdk/anthropic); SignalInsightsBar 5 Badges mit AI-Tooltip; trading/page.tsx symbol/timeframe verdrahtet
> - Rev. 24 (17.03.2026): AC90/AC93 done — `AskAiContextMenu.tsx` NEU (shadcn ContextMenu Wrapper, reusable); `TradingWorkspace.tsx` refactored (manuelles Kontextmenu entfernt, AskAiContextMenu + symbol/timeframe Props); `trading/page.tsx` verdrahtet; `SplitChatShell` Rail-Mode (240px persistent); Spec AC90/AC93 auf [x] gesetzt
> - Rev. 22 (17.03.2026): Phase 22f complete — AC39/AC49b/AC51c/AC52/AC53/AC54/AC55/AC56/AC64/AC101/AC104/AC108 done; AttachmentPreviewStrip+ImagePreviewModal NEU; AgentChatTtsButton auf BFF TTS+WebAudio; AgentChatComposer +paperclip+drag+drop+paste; AgentChatMessage +image-thumbnails+cost-badge; AgentChatMarkdown +citation-superscript; AgentChatEventRail +context-pressure-bar; AgentChatToolbar +reasoning-effort-cycle; useChatSession +nuqs-URL-chatId+attachments+cost+reasoningEffort; BFF+Go+Python multimodal+reasoningEffort end-to-end; Biome 0 Fehler
> - Rev. 21 (17.03.2026): Phase 22f partial — AC103/AC106/AC107 done; `useChatSession.ts` + `onFinish` Usage-Map (`promptTokens/completionTokens/finishReason` per messageId); `AgentChatToolbar.tsx` controlled (selectedModel/onModelChange props); BFF+Go+Python: `model` override per Request durchgezogen; `AgentChatMessage.tsx`: Token-Badge (↑↓ Tokens, finishReason tooltip) auf sealed assistant messages; Biome 0 Fehler

---

## Implementierungsstand (Rev. 10)

### Abgeschlossen — Frontend Core (Phase A) + Rich-Text/Speech (Phase B) + SDK-Migration (Phase 22d)

TypeCheck (tsc --noEmit): Biome 0 Fehler. tsc: 3 pre-existing Fehler (nicht Phase-22d-verursacht, Fix-Batch ausstehend — siehe Sektion R CHECKPOINT).

| Datei | Verantwortung |
|---|---|
| `AgentChatPanel.tsx` | Thin orchestrator |
| `hooks/useChatSession.ts` | `useChat` + `DefaultChatTransport` + `prepareSendMessagesRequest` (Phase 22d) |
| `components/AgentChatHeader.tsx` | Header + Control-Entry-Link |
| `components/AgentChatThread.tsx` | Thread + scroll/autofollow + Empty-State + Suggestion-Chips |
| `components/AgentChatMessage.tsx` | Message-Bubble + Markdown + Copy-Button |
| `components/AgentChatMarkdown.tsx` | react-markdown + GFM + Syntax-Highlighting + Think-Box |
| `components/AgentChatToolBlock.tsx` | Collapsible tool_call/tool_result |
| `components/AgentChatComposer.tsx` | Input (auto-resize) + Send/Stop + Mic (Web Speech API) |
| `components/AgentChatErrorBanner.tsx` | Error-Banner + dismiss |
| `app/api/agent/chat/route.ts` | BFF SSE-Proxy → Go Gateway |

### Backend-Status (Stand 18.03.2026)

- ~~Go Gateway: `/api/v1/agent/chat` SSE-Endpoint~~ → **code-complete (AC6, Phase 22g)**
- ~~Python agent-service: Chat-Handler + Streaming~~ → **code-complete (AC7, Phase 22g)** — `run_agent_loop()` in `python-agent/agent/loop.py`
- Thread-Persistenz via `AgentEpisode` (AC10/AC11) — **noch offen**

---

## 0. Execution Contract

### Scope In

- Frontend Chat-UI ueber Agent-Layer (Go Gateway -> Python memory-service -> LLM)
- SSE-Streaming mit `chunk`, `done`, `tool`, `error`, `block`, `updateBlock`, `stream_status` Events
- Message-Thread-Management inkl. Persistenzanbindung (`AgentEpisode`)
- Tool-Call-Visualisierung (collapsible, timeline)
- Markdown-Rendering mit Syntax-Highlighting, Code-Copy, `<think>`-Box
- Speech-Input (Whisper/WebSpeech) + TTS-Output (Browser SpeechSynthesis)
- Message-Actions: Copy, Regenerate, Edit, Feedback (thumbs up/down)
- File-Attachment-Lifecycle (staged, preview, send, remove)
- Sources/Citations Panel unter assistant messages
- Frontend-nahe Security-Boundaries (kein browser-direkter Tool-Wirkpfad)
- SDK-Entscheid (no-SDK-first, Evaluate-Track TanStack AI / Vercel AI SDK)

### Scope Out

- Agent-Business-Logic in Python
- tiefe Memory-KG-/Vector-Store-Strategien ausser Chat-bezogener Persistenznutzung
- Keyboard-Shortcuts (eigenstaendiger Slice: `command_keyboard_delta.md`)
- generelle Frontend-Styling- und Design-System-Refactors ausser Chat-Surface

### Priorisierungsregel (verbindlich)

1. Chat-Core (bereits erledigt)
2. Frontend-only Erweiterungen (kein Backend noetig): Markdown, Code-Blocks, Speech, TTS, Copy, Think-Box
3. Backend-abhaengige Erweiterungen: Regenerate, Edit, Attachments, Feedback, Sources
4. SOTA-2026 Features: Extended Thinking, Structured Outputs, Multi-Modal Image
5. SDK-Track + Harness-Hardening

### Mandatory Upstream Sources

- `docs/specs/FRONTEND_ARCHITECTURE.md`
- `docs/specs/execution/frontend_enhancement_delta.md`
- `docs/specs/execution/agent_harness_runtime_delta.md`
- `docs/frontend_chat_ui.md`
- `docs/AGENTS_BACKEND.md` (fuer backendseitige Einordnung externer Referenzen, inkl. Tambo)
- `docs/AGENT_SECURITY.md` / `docs/AGENT_TOOLS.md` / `docs/GO_GATEWAY.md`

### Optional References (nur bei Bedarf)

- `docs/AGENT_CODE_MODE.md` (nur relevant, falls spaeter UI-Interop fuer komprimierte High-Volume-Payloads aktiviert wird)

- arXiv (11.03.2026): `The Attack and Defense Landscape of Agentic AI`
  — https://arxiv.org/pdf/2603.11088

---

## 1. Offene Deltas

### A. Chat-Core UI

- [x] **AC1** `AgentChatPanel` von Stub auf produktionsnahe Grundstruktur gebracht
- [x] **AC2** Composer-Funktionen (send, disabled/pending, enter/shift-enter, restore-on-failure)
- [x] **AC3** Message-Thread Rendering (user/assistant getrennt, progressive updates)
- [x] **AC4** Fehler-/Leerlauf-/Initial-Zustaende (empty, streaming-dots, error banner, retry CTA)

### B. Streaming & Transport

- [x] **AC5** Next BFF `/api/agent/chat` SSE-Proxy verdrahtet
- [x] **AC6** Go Gateway `/agent/chat` SSE-Endpoint — **code-complete (Phase 22g, 18.03.2026)**
  - `go-backend/internal/handlers/http/agent_chat_handler.go`: SSE-Proxy → Python agent-service `:8094`; UIMessage-Stream-Header; Approval-Stub `POST /api/v1/agent/approve`
  - _Live-Verify: ACR.V5–V13 offen (Sprint 3)_
- [x] **AC7** Python agent-service Chat-Handler + Streaming — **code-complete (Phase 22g, 18.03.2026)**
  - `python-agent/agent/app.py` + `loop.py`: `_stream_agent_loop()` → `run_agent_loop(ctx, messages)` → Vercel AI Data Stream Protocol SSE
  - LLM-agnostisch: `AGENT_PROVIDER=anthropic|openai|openai-compatible` (Anthropic SDK + OpenAI SDK; deckt OpenRouter/Ollama/vLLM ab)
  - `ToolRegistry.load()` 6 Standard-Tools; `CapabilityEnvelope` + `validate_tool_call()` vor jedem Execute
  - _Live-Verify: ABP.V1-LV–V3-LV offen (Sprint 3)_
- [x] **AC8** Event-Mapping (`chunk`, `done`, `tool`, `error`) inkl. Idempotenz-Regeln
- [ ] **AC9** Reconnect-/Degradation-Pfad mit Interruption-Policy (`stop` xor `resume`)
  - Stop-Mode: `stop` beendet Run terminal; nur Retry/Regenerate startet neuen Run
  - Resume-Mode: reconnect auf aktiven Run erlaubt (kein `stop` im selben Modus)

### C. Thread & Persistenz

- [ ] **AC10** Thread-Lifecycle auf `AgentEpisode` abbilden (Frontend vorbereitet via `threadIdRef`)
- [ ] **AC11** Reload-Restore (benoetigt AC10)
- [ ] **AC12** Thread-History UX (list/search/new/fork)

### D. Tool-Event UX

- [x] **AC13** Tool-Event-Visualisierung als collapsible Eintraege (`AgentChatToolBlock.tsx`)
- [x] **AC14** tool_call + tool_result als Paar, durationMs, collapsed by default
- [ ] **AC15** Message-Action Contract (copy/retry/regenerate/stop je nach status)

### E. Frontend-nahe Harness/Security-Grenzen

- [x] **AC16** Kein browser-direkter Tool-Wirkpfad (alle Aktionen via BFF/Gateway)
- [x] **AC17** read-only/bounded-write Markierung sichtbar (Composer-Footer)
- [ ] **AC18** Audit-faehige Event-Spur im Chat-Kontext (benoetigt Backend-Persistenz)

- 16.03.2026 Vermerk vor SDK-Track: `src/app/api/agent/chat/route.ts` erzwingt jetzt einen strict BFF-Envelope (`message`, `threadId`, `agentId`) und blockiert unerwartete Tool-/Scope-/Write-Felder mit `INVALID_CHAT_PAYLOAD`; negative Regressionstests liegen in `src/app/api/agent/chat/route.test.ts`.

### F. SDK/Provider Evaluate-Track

- [ ] **AC19** TanStack AI vs. Vercel AI SDK vs. no-SDK evaluieren
- [ ] **AC20** SDK-Entscheid dokumentieren (aktuell: kein SDK — eigener Transport, stabil und Gateway-konform)
- [ ] **AC21** Gateway `LLM_PROVIDER` Track (Anthropic/Ollama/vLLM)
- [ ] **AC22** Ollama/vLLM dev-opt-in Nachweise
- [ ] **AC22a** Tambo-Backend-Relevanz geprueft und dokumentiert (component/event contracts, thread protocol framing) — Ownership ueber `AGENTS_BACKEND.md`, kein impliziter Transport-Switch

### G. Onyx-Robustheit

- [x] **AC25** Session-isolierter Chat-State (in-flight, error, abort-controller) — `useChatSession.ts`
- [x] **AC26** Scroll-/Autofollow (auto-follow nur bei "at bottom") — `AgentChatThread.tsx`
- [x] **AC28** Stream-Parser-Robustheit (partial-frame buffering, malformed frames geskippt)
- [x] **AC29** Terminal-Event-Idempotenz (`done` nur einmal via `inFlightId`-Guard)
- [x] **AC33** Composer-Optimistic-Submit + restore-on-failure
- [ ] **AC23** Packet-Metadaten (`turn_index`, `tab_index`) fuer stabile Reihenfolge
- [ ] **AC24** Message-Tree-Branching (regenerate/fork/switch)
- [ ] **AC27** Message-Toolbar-Action-Vertrag (copy/retry/regenerate/sources zustandsabhaengig)
- [ ] **AC30** Placeholder->Real-Thread-Migration bei Reload
- [ ] **AC31** Poll/Reload-Merge-Policy (dedupe per messageId, stabile Sortierung)
- [ ] **AC32** Queue-Concurrency-Contract (sequential queue, pending-upload guard)

---

### H. Markdown & Rich Text (NEU — aus Clone-Analyse)

- [x] **AC34** Markdown-zu-JSX-Parser — `react-markdown` + `remark-gfm` in `AgentChatMarkdown.tsx`
- [x] **AC35** Syntax-Highlighting — Prism via `react-syntax-highlighter` + Sprach-Label
- [x] **AC36** Code-Block Copy-Button mit "Copied!"-Feedback (1.5s)
- [x] **AC37** Tabellen-Rendering via GFM (custom `table/th/td` renderer mit overflow-scroll)
- [x] **AC38** `<think>`-Tag Collapsible-Box — `splitThinkBlocks()` Preprocessor + `ThinkBlock` Component; collapsed by default
- [x] **AC39** Inline-Citation-Rendering — `[N]`-Muster via `renderWithCitations()` in `AgentChatMarkdown` `p`-Renderer als Superscript-Badge (`<sup>`) gerendert; kein neues Package noetig
- [x] **AC40** Textarea Auto-Resize — `resizeTextarea()` in onChange, max-h 160px

### I. Message Actions & Toolbar (NEU)

- [x] **AC41** Copy-Button pro assistant-Message — `CopyButton` in `AgentChatMessage.tsx`; nur bei sealed (nicht streaming) messages sichtbar
- [x] **AC42** Regenerate/Rewrite-Button — `RotateCcw`-Button im Footer der letzten Assistant-Message (`isLast && onRegenerate`); ruft `retry()` aus `useChatSession` auf (Vercel AI SDK `regenerate`); verdrahtet in `AgentChatPanel` → `AgentChatThread` → `AgentChatMessage`; `memo`-Comparator um `isLast` erweitert
  - Referenz: Perplexica `MessageActions/Rewrite.tsx`, Onyx
  - benoetigt: Backend (Thread-Kontext + neuer SSE-Call)
- [x] **AC43** User-Message inline editieren — implementiert als AC105 (Pencil-Icon → Textarea → Cancel/Resend; `editAndResend()` in `useChatSession`)
  - Referenz: Onyx `HumanMessage.tsx` + `MessageEditing` component
  - benoetigt: Backend (Message-Tree-Recalculation)
- [x] **AC44** Feedback-Buttons — `ThumbsUp`/`ThumbsDown` im Footer jeder sealed Assistant-Message; lokaler Toggle-State (`feedback: "up"|"down"|null`); visuelles Feedback (emerald/red); kein Backend-Call (Persistenz via FC15 ausstehend)
  - Thumbs-Down → optionaler Feedback-Modal mit Textfeld
  - Referenz: Onyx `MessageToolbar.tsx` + `FeedbackModal.tsx`
  - benoetigt: Backend (Feedback-Persistenz)
- [ ] **AC45** Message-Switching (Prev/Next zwischen alternativen Antworten)
  - Referenz: Onyx `MessageSwitcher.tsx`
  - benoetigt: Backend (Message-Tree)
- [x] **AC46** Paced Turn Groups — `motion.div` mit `delay = min(index * 0.04, 0.15)s` fade-in in `AgentChatMessage`; keine externe Hook-Abhaengigkeit noetig

### J. Speech Input & TTS (NEU)

- [x] **AC47** Voice-Input-Button im Composer — `useSpeechInput` Hook mit Web Speech API; States: inactive/listening/processing; Transcript → append to input; Mic hidden auf nicht-unterstuetzten Browsern
- [ ] **AC48** VAD fuer Phase 2 (Whisper) — ausstehend; Web Speech API hat eigenes VAD ✓
- [x] **AC49** TTS-Button pro assistant-Message — `AgentChatTtsButton.tsx`; SpeechSynthesis; emoji-strip; Play/Stop toggle; TTS-Exklusivitaet via `speakingId` in Thread
- [x] **AC50** TTS-Autoplay-Queue — `autoplayTts` state in `useChatSession`; Toggle-Button (Volume2/VolumeX) in `AgentChatToolbar`; autoplay-useEffect in `AgentChatThread` (letzte sealed assistant Message → Web Audio API fetch + play)

### K. File Attachments (NEU)

- [x] **AC51** Paperclip-Button im Composer mit Count-Badge — `attachments.length > 0` → roter Badge `-top-0.5 -right-0.5` mit Zahl; `relative` auf Button-Wrapper
  - Referenz: Perplexica `MessageInputActions/Attach.tsx`
- [x] **AC52** Staged-Attachment-Preview — `AttachmentPreviewStrip.tsx` NEU; horizontaler Scroll-Strip mit Thumbnails + Remove-Button; ObjectURL-Lifecycle in `useAttachments.ts`
- [x] **AC53** Drag & Drop + Clipboard-Paste — `onDragOver`/`onDrop`/`onPaste` in `AgentChatComposer`; isDragging-State mit visueller Feedback; Chart-Screenshot Paste direkt unterstuetzt
- [x] **AC54** Image-Thumbnails in User-Messages — `AgentChatMessage` rendert `stagedAttachments` prop als klickbare 64px-Thumbnails; `AgentChatThread` mappt `sentAttachments[][]` nach User-Message-Reihenfolge
- [x] **AC55** Image-Preview Modal — `ImagePreviewModal.tsx` NEU; Fullscreen-Lightbox; Zoom +/-; Esc-Close; rendered als Portal in Composer + Message
- [x] **AC56** Multi-Modal Image Input — `useAttachments` hook (`StagedAttachment`+`RequestAttachment`, `toRequestAttachments()` Base64); BFF-Schema (`attachmentSchema` Zod); Go `agentAttachment`+`agentChatRequestBody.Attachments`; Python `ImageAttachment`+`_build_user_content()` (Anthropic image blocks + OpenAI `image_url` data-URI)

### L. Sources & Citations Panel (NEU)

- [x] **AC57** Sources-Panel unter assistant-Message (Source-Cards: Favicon + Titel + Domain)
  - "View N more" → shadcn Dialog mit allen Quellen
  - `AgentChatSources.tsx` NEU — `extractSources()` liest aus `message.annotations` + `data`-Parts
  - Perplexica-inspiriertes Card-Layout (Globe-Icon, Titel, Domain, Snippet 2-line-clamp)
- [x] **AC58** Source-Tag-Button (Quellen-Count-Badge) — in AgentChatSources Header integriert
  - `{sources.length}` Badge neben "Sources" Label; "View N more" Dialog bei overflow

### M. Assistant Steps & Reasoning (NEU)

- [ ] **AC59** Assistant-Steps-Timeline (collapsible Reasoning-Schritte: Thinking → Searching → Reading)
  - Referenz: Perplexica `AssistantSteps.tsx` mit motion-Animationen
  - benoetigt: Backend (neue SSE-Event-Typen: `step_start`, `step_done`)
- [ ] **AC60** Extended-Thinking-Block (Claude 3.7 Sonnet) als eigener Block-Typ `thinking`
  - Collapsed by default, "Extended Thinking" Header mit Token-Count
  - SOTA-2026: Pflicht fuer Anthropic-Integration
  - benoetigt: Backend (Anthropic `thinking` blocks parsen + forwarden)

### N. Empty State & Loading (NEU)

- [x] **AC61** Empty-Chat-Screen mit Suggestion-Chips — 4 kontextuelle Starter-Prompts in `AgentChatThread.tsx`; Click → `onSuggestion` → `send()`
- [x] **AC62** Loading-Skeleton — `MessageSkeleton` Shimmer-Komponente; erscheint bei `isConnecting && messages.length === 0`

### O. Structured Outputs & Custom Tool Renderers (NEU — SOTA 2026)

- [x] **AC63** Structured-Output-Renderer — `JsonRenderer` in `AgentChatMarkdown`; Array of objects → collapsible table; plain objects → key-value card; nur bei explizitem ` ```json ` + multiline ausgeloest; Fallback → CodeBlock
  - SOTA-2026: Anthropic/OpenAI JSON-Mode
  - Referenz: Onyx `CustomToolRenderer.tsx`
- [x] **AC64** Context-Window-Pressure-Bar — `AgentChatEventRail` zeigt farbige 2px-Bar unter Status-Rail; Farbe: gruen→amber→orange→rot ab 50%/75%/90%; `contextPressure` (0-1) aus `latestPromptTokens / MODEL_MAX_CONTEXT` in `useChatSession`; `%ctx`-Label in Rail
- [ ] **AC65** Prompt-Caching-Badge (cache_creation/cache_read tokens anzeigen)
  - SOTA-2026: Anthropic-spezifisch, Cost-Awareness fuer Trader
  - benoetigt: Backend (Gateway muss Token-Usage forwarden)
- [x] **AC66** Agent-Tool-Approval-Flow im Chat (vor kritischen Tool-Calls muss User approven)
  - `AgentChatToolBlock` Approval-Card bei `state === "approval-requested"` (ShieldAlert + Approve/Deny)
  - `approveToolCall`/`denyToolCall` in `useChatSession` → POST `/api/agent/approve` → Go Gateway
  - Chain: useChatSession → AgentChatPanel → AgentChatThread → AgentChatMessage → AgentChatToolBlock
  - BFF: `src/app/api/agent/approve/route.ts` (POST, proxied to Go `/api/v1/agent/approve`)

### P. UX-Polish & Accessibility (NEU)

- [x] **AC67** React.memo — `AgentChatMessage` (custom arePropsEqual: id/content/streaming/errorText/blocks.length/speakingId-relevance), `AgentChatToolBlock` (id/isCollapsed/toolResult), `AgentChatMarkdown` (content-only)
- [x] **AC68** Focus-Management — `AgentChatComposer` als `forwardRef<AgentChatComposerRef>` mit `useImperativeHandle`; `focus()` via `onMounted` in `AgentChatPanel` nach oben gereicht; Retry + Speech-Transcript fokussieren Textarea
- [ ] **AC69** `stream_status` + `block` + `updateBlock` SSE-Events im Frontend-Parser
  - `stream_status`: live/degraded/recovered Handling + `AgentChatEventRail`-Update
  - `block`: neuer typisierter Block (text/tool_call/tool_result/thinking/citation_list/warning/suggestion)
  - `updateBlock`: patch block by id (partial streaming updates)
  - zusaetzlich: metadata/data-parts Trennung (persistent vs transient) fuer history-safe rendering
  - benoetigt: BFF-Erweiterung + Go-Gateway-Forwarding
- [x] **AC70** `AgentChatEventRail` — Status-Badge (idle/live/degraded/reconnecting) + Latenz + Provider-Label; unterhalb Toolbar
- [x] **AC71** `AgentChatToolbar` — Model-Selector (statisch: Sonnet/Opus/Haiku) + Context-Reset + New-Thread Buttons; dynamic model-list wartet auf Backend
- [x] **AC72** `AgentChatReconnectBanner` — getrennt vom Error-Banner; States: reconnecting/degraded/recovered (auto-dismiss 2.5s)
- [ ] **AC73a** `stop_generation` Contract (UI + Gateway)
  - `stop()` beendet Generation terminal; kein Resume derselben Generation
  - benoetigt: Backend + UI-State (`stopped_by_user`)
- [ ] **AC73b** `resume_stream` Contract (nur Resume-Mode)
  - reconnect auf aktiven Stream via Resume-Endpoint; `204` wenn kein aktiver Stream
  - benoetigt: activeStreamId-Persistenz + Resume-Endpoint
- [ ] **AC73c** `pause_loop_resume_loop` Evaluation (Agent-Loop, nicht Token-Stream)
  - Ziel: Workflow/Graph-Checkpointing fuer human-in-the-loop Pause/Resume
  - explizit getrennt von `stop_generation` und `resume_stream`
  - benoetigt: Backend-Orchestrierung (Go/Python), nicht reines Frontend-SDK

---

## 2. Verify-Gates

### Implementiert / testbar (Rev. 9 Status unveraendert)

- [x] **AC.V1** Nachricht senden → chunks sichtbar (E2E benoetigt Go Gateway)
- [x] **AC.V4** Tool-Events als kollabierbare Eintraege
- [x] **AC.V5** Fehlerfall → Error-Banner + Retry; keine silent failures
- [x] **AC.V6** Kein browser-direkter Tool-Wirkpfad
- [x] **AC.V7** read-only/bounded-write Kennzeichnung sichtbar
- [x] **AC.V10** Chat → Control Einstieg vorhanden
- [x] **AC.V11** Packet-Placement deterministisch
- [x] **AC.V13** Session-Wechsel keine State-Leaks
- [x] **AC.V14** Partial/fragmentierte Frames robust verarbeitet
- [x] **AC.V15** Doppelte Terminal-Events ohne Duplikat-Persistenz
- [x] **AC.V19** Composer restore-on-failure

### Neu hinzugefuegt (Rev. 10)

- [ ] **AC.V20** Markdown wird korrekt gerendert (bold, italic, lists, headings)
- [ ] **AC.V21** Code-Blocks syntaxhighlighted + Copy-Button funktioniert
- [ ] **AC.V22** `<think>`-Block collapsed by default; aufklappbar; kein Layout-Shift
- [ ] **AC.V23** Voice-Input: Mic-Button → LISTENING → RECORDING → PROCESSING → Text in Composer
- [ ] **AC.V24** TTS: Speaker-Button → liest Message vor; Stop-Button stoppt; keine gleichzeitigen TTS-Instanzen
- [~] **AC.V25** Speech: STT via BFF `/api/audio/transcribe` (MediaRecorder-Fallback); TTS via `/api/audio/synthesize` — kein direkter Browser-zu-Provider-Aufruf mehr (AC47b/AC49b geaendert)
- [ ] **AC.V26** Attachment: Datei attachen → Preview → senden → Datei-Display in Message
- [ ] **AC.V27** Empty-Chat-Screen zeigt Suggestion-Chips; Click fuellt Composer
- [ ] **AC.V28** `stream_status: degraded` → ReconnectBanner erscheint; `recovered` → Banner verschwindet
- [ ] **AC.V29** Extended-Thinking-Block sichtbar bei Claude 3.7-Responses (E2E)
- [ ] **AC.V30** Agent-Tool-Approval-Card erscheint im Thread vor kritischen Tool-Calls
- [ ] **AC.V31** Context-Window-Pressure-Bar visible bei >80% Usage
- [ ] **AC.V48** Stop-Mode: `stop()` beendet Run; reconnect resumiert denselben Run nicht
- [ ] **AC.V49** Resume-Mode: Disconnect ohne stop -> Resume auf denselben aktiven Run
- [ ] **AC.V50** Resume-Endpoint ohne aktiven Stream liefert `204 No Content`
- [ ] **AC.V51** Approval-Flow: approve/deny + continuation ohne Deadlock
- [ ] **AC.V52** Duplicate terminal events (`done`/`text-end`) bleiben idempotent

### Phase B–D / 22c — ergaenzte Verify-Gates (Rev. 19)

_(ACs waren implementiert, hatten aber bisher keine Verify-Gate-Eintraege)_

- [ ] **AC.V59** AC41: Copy-Button erscheint auf sealed (nicht streaming) assistant-Messages; Klick → "Copied!"-Feedback fuer 1.5s sichtbar; Button verschwindet waehrend Streaming
- [ ] **AC.V60** AC46: Neue Nachrichten erscheinen mit sanftem Fade-in (kein harter Einsprung); sichtbar bei mehreren schnell eintreffenden Messages; kein Layout-Shift
- [ ] **AC.V61** AC67/68: Composer-Textarea fokussiert automatisch beim Oeffnen des Chat-Panels (kein manueller Klick noetig); Fokus bleibt nach Retry und nach Speech-Transcript-Insert
- [ ] **AC.V62** AC70: EventRail unterhalb der Toolbar sichtbar; zeigt Status-Badge (idle/live/degraded/reconnecting); Latenz-Label und Provider-Label vorhanden; Status aendert sich bei `stream_status`-Events
- [ ] **AC.V63** AC71: Toolbar zeigt Model-Selector mit drei Optionen (Sonnet/Opus/Haiku); Context-Reset-Button vorhanden; New-Thread-Button vorhanden; keine Funktions-Regression bei Klick auf Context-Reset

### Offen — blockiert auf Backend

- [ ] **AC.V2** Stream-Unterbruch → Reconnect
- [ ] **AC.V3** Thread nach Reload konsistent wiederhergestellt
- [x] **AC.V8** SDK-Entscheid dokumentiert — siehe Sektion Q
- [ ] **AC.V9** Fallback-Polling bei SSE-Ausfall
- [ ] **AC.V12** Regenerate/Fork konsistentes Branching
- [ ] **AC.V16** Placeholder→Real-Thread bei Reload deterministisch
- [ ] **AC.V17** Poll/Reload-Merge keine Duplikate
- [ ] **AC.V18** Queue mit pending uploads sicher

---

### Q. Global-Overlay-Architektur (Phase 22c — vor SDK-Migration)

> **Reihenfolge:** Global-Overlay zuerst (22c), danach SDK-Migration (22d).
> **Grund:** `(shell)/layout.tsx` ist der korrekte Mount-Point — stabiler als Trading-only. SDK-Migration danach als sauberer Slice.

**App-Struktur-Aenderung (andere Instanz, 14.03.2026):**
Alle Haupt-Routen liegen jetzt in `src/app/(shell)/`:
- `(shell)/trading/page.tsx`, `(shell)/control/[[...tab]]/page.tsx`, `(shell)/geopolitical-map/page.tsx`, `(shell)/files/[[...tab]]/page.tsx`
- `(shell)/layout.tsx` — gemeinsames Shell-Layout mit `GlobalTopBar`
- Auth-Routen (`/auth/*`) bleiben aussen — kein Chat/Overlay dort. Korrekt.

**Global-Overlay Mount-Point:** `src/app/(shell)/layout.tsx`

```tsx
// (shell)/layout.tsx — SOLL nach Phase 22c
export default function ShellLayout({ children }) {
  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <GlobalTopBar />
      <GlobalKeyboardProvider />   // ⌘L, ⌘⇧A, ⌘⇧M, ⌘⇧C, ⌘T global
      <GlobalChatOverlay />        // AgentChatPanel als Sheet/Drawer
      <div className="flex flex-1 flex-col overflow-hidden">{children}</div>
    </div>
  );
}
```

**CommandPalette-Migration:** Aus `(shell)/trading/page.tsx` raus → in Shell-Layout oder `GlobalKeyboardProvider`. Damit wird `⌘K` auch auf `/control`, `/geopolitical-map`, `/files` verfuegbar.

- [x] **AC74** `GlobalKeyboardProvider` in `(shell)/layout.tsx` — ⌘K/⌘L/⌘T/⌘⇧M/⌘⇧C global; `CommandPalette` nach `src/components/CommandPalette.tsx` verschoben; `onOpenChat` prop entfernt → `useGlobalChat()` intern; Trading-Props optional (Symbol/TF nur auf /trading); Geo/trading/global alle auf `@/components/CommandPalette`
- [x] **AC75** `GlobalChatOverlay` in `(shell)/layout.tsx` — `AgentChatPanel` als `Sheet side=right modal=false`; `open`-State via `GlobalChatContext`; focus via `onMounted`
- [x] **AC76** `⌘T` → `/trading` in `GlobalKeyboardProvider` registriert
- [x] **AC77** `onOpenChat` prop geschlossen — `CommandPalette` + `GlobalTopBar` nutzen `useGlobalChat()` direkt; kein prop-drilling

**Verify-Gates (Phase 22c):**
- [x] **AC.V32** `⌘K` oeffnet CommandPalette von `/control`, `/geopolitical-map`, `/files` (nicht nur `/trading`) — verifiziert 23.03.2026
- [x] **AC.V33** `⌘L` oeffnet Chat-Overlay von jeder Shell-Seite — verifiziert 23.03.2026
- [ ] **AC.V34** Chat-Overlay bleibt offen bei Navigation zwischen Shell-Seiten (kein Remount)
- [ ] **AC.V35** `⌘T` navigiert zu `/trading` von jeder Shell-Seite

---

### R. Vercel AI SDK Migration (Phase 22d — nach Global-Overlay)

> **Status:** **CODE-COMPLETE** (17.03.2026) — `ai@6.0.116` + `@ai-sdk/react@3.0.118` migriert; Live-Verify-Gates offen (Stack noetig).
> **Entscheid:** Vercel AI SDK v6 (`@ai-sdk/react`) — implementiert.
> **TanStack AI:** Abgelehnt — Alpha 0.3.x (Maerz 2026), kein stabiles Release.
> **Eigener Transport (alt):** ersetzt durch `DefaultChatTransport` + `prepareSendMessagesRequest`.
> **Wichtig:** `stop/abort` und `resume` sind im Standardpfad nicht als ein gemeinsames Interruptionsmodell zu behandeln.

**Warum AI SDK:**

| Feature | Ohne SDK (IST) | Mit AI SDK |
|---|---|---|
| Extended Thinking Blocks | `<think>` Tag-Parsing (AC38) | First-class `reasoning` part, built-in |
| Tool-Call 4-State UI | Manuell `tool_call/tool_result` Pair | Built-in `input-streaming/available/output-available/error` |
| Typed Message Parts | Eigene `ChatBlock[]` Types | `message.parts` — vollstaendig typisiert |
| Message Resume bei Reconnect | AC9 offen | Built-in (nur im Resume-Mode; nicht als stop+resume Kombi) |
| File Attachments | AC51-56 manuell | `experimental_attachments` built-in |
| Structured Outputs | AC63 manuell | Built-in via `streamText` + `output` |

**Kein Vercel-Lock-in:** Data Stream Protocol ist offener Spec. Go Gateway emittiert ihn, bleibt volle Eigenkontrolle.

**Migrations-Schutz vor Vermischung (verbindlich):**

- 22d startet erst nach Abschluss der Interruption-Policy (`AC9`, `AC73a`, `AC73b`).
- `AC73c` (Pause-Loop/Resume-Loop) ist **separate** Evaluation und kein Blocker fuer 22d.
- Keine implizite Aussage "ChatGPT-artiges pause/resume" fuer reines SDK-Upgrade.

**Go Gateway — einmalige Protocol-Migration:**
```
// Header hinzufuegen:
w.Header().Set("x-vercel-ai-ui-message-stream", "v1")

// Event-Format aendern:
// Alt: data: {"type":"chunk","delta":"Hello"}
// Neu: data: {"type":"text-start","id":"t1"}
//      data: {"type":"text-delta","id":"t1","delta":"Hello"}
//      data: {"type":"text-end","id":"t1"}

// Extended Thinking gratis:
//      data: {"type":"reasoning-start","id":"r1"}
//      data: {"type":"reasoning-delta","id":"r1","delta":"..."}
//      data: {"type":"reasoning-end","id":"r1"}
```

**Was ersetzt wird:**
- `useChatSession.ts` → `useChat` aus `@ai-sdk/react`
- `parseSSEFrame` + Buffer-Logik → entfaellt
- `/api/agent/chat/route.ts` BFF → schlankes Proxy (nur Header + Auth-Weiterleitung)
- Manuelles `SseChunkEvent / SseDoneEvent / SseToolEvent` → SDK `UIMessage` Types

**Was bleibt:**
- `AgentChatMarkdown.tsx` — eigenes Rendering ist besser als SDK-Default
- `AgentChatPanel.tsx` Struktur (Orchestrator-Pattern)
- Alle Sub-Komponenten (Composer, Thread, Message, ToolBlock, TTS, EventRail, Toolbar)
- Go Gateway Architektur

**ACs Phase 22d:**
- [x] **AC78** `bun add ai @ai-sdk/react @ai-sdk/anthropic` — `ai@6.0.116` + `@ai-sdk/react@3.0.118` installiert
- [x] **AC79** Go Gateway: `x-vercel-ai-ui-message-stream: v1` Header + typisiertes Event-Format — impl in `agent_chat_runtime_delta.md` (AC-G2 done)
- [x] **AC80** `useChatSession.ts` ersetzt durch `useChat` + `DefaultChatTransport` + `prepareSendMessagesRequest`; maps SDK body → BFF `{message, threadId}`
- [x] **AC81** BFF `/api/agent/chat/route.ts` — SSE-Proxy mit `x-vercel-ai-ui-message-stream: v1` Header + `error`→`errorText` Rewrite fuer ai v6 DefaultChatTransport
- [x] **AC82** `AgentChatMessage.tsx` auf `UIMessage` + `message.parts` umgestellt (TextUIPart / ReasoningUIPart / DynamicToolUIPart)
- [x] **AC83** `AgentChatMarkdown.tsx` unveraendert — wird an `part.text` (TextUIPart) uebergeben
- [x] **AC84** Extended Thinking via `ReasoningUIPart` (`part.type === "reasoning"`, `part.text`) → `ReasoningBlock` Collapsible-Component in `AgentChatMessage.tsx`
- [x] **AC85** Tool-Call 7-State UI via `DynamicToolUIPart` — `input-streaming|input-available|output-available|output-error|output-denied|approval-requested|approval-responded`; in `AgentChatToolBlock.tsx`
- [x] **AC86** `ChatBlock / ChatMessage / SseChunkEvent / SseDoneEvent / SseToolEvent / SseErrorEvent / ChatSessionState` aus `types.ts` entfernt; nur `AgentChatConfig` + `ChatThread` verblieben

> **⚠ CHECKPOINT — Pre-existing tsc Fehler (nicht von Phase 22d verursacht):**
> - `src/app/api/admin/users/route.ts:65,108` — `HeadersInit` type mismatch (`x-auth-user-id: string | undefined`). Ursache: Codex Go-Ownership-Migration. Fix: `?? ""` Fallback ergaenzen.
> - `src/lib/server/passkeys.ts:576,577` — `string | null | undefined` nicht assignable zu `string | null` bzw. `string`. Ursache: Codex vierter Ownership-Schnitt. Fix: `?? null` / `?? ""` Fallback ergaenzen.
> - `scripts/merge-frontend-sqlite-into-backend-sqlite.ts:4` — `bun:sqlite` Modul nicht in tsconfig. Fix: `tsconfig.json` mit `bunTypes` ergaenzen oder exclude.
> **→ Alle drei in einem separaten Fix-Batch nach Slice-Abschluss schliessen (AC.V39 pending bis dann).**

**Verify-Gates Phase 22d:**
- [ ] **AC.V36** `useChat` sendet + empfaengt SSE korrekt ueber Go Gateway (Live-Stack)
- [ ] **AC.V37** Extended Thinking Block erscheint via `reasoning` Part (kein `<think>` Tag noetig) (Live-Stack)
- [ ] **AC.V38** Tool-Call zeigt alle 7 States korrekt (input-streaming / input-available / output-available / output-error / output-denied / approval-requested / approval-responded) (Live-Stack)
- [x] **AC.V39** tsc 0 Fehler, Biome 0 Fehler nach Migration — alle 3 Codex-pre-existing Fehler gefixt (admin/users `?? ""`, passkeys `?? null`/`?? ""`, tsconfig scripts exclude); IndicatorAiTooltip `ai/react`→`@ai-sdk/react`; AgentChatSources auf echte SDK-Typen; useChatSession `onFinish.usage`→`message.metadata`; tsconfig ES2022
- [ ] **AC.V40** Kein Regression in bestehenden Chat-Features (Markdown, TTS, Voice, Copy, Suggestion-Chips) (Live-Stack)
- [ ] **AC.V53** 22d respektiert Mode-Gating: Stop-Mode und Resume-Mode bleiben getrennt
- [ ] **AC.V54** Metadata + transient data parts werden ohne History-Verschmutzung verarbeitet
- [ ] **AC.V55** Abort/Finish cleanup verifiziert (keine dangling active streams)

**Reihenfolge / Verweis (Frontend-first):**

- Solange 22d nicht abgeschlossen ist (`AC78..AC86` + `AC.V36..AC.V40`), bleiben
  `docs/specs/execution/agent_harness_runtime_delta.md` und
  `docs/specs/execution/agent_backend_program_delta.md` unveraendert.
- Nach Abschluss von 22d wird **einmalig** dort harmonisiert:
  - identische Interruption-Semantik (`stop` xor `resume`)
  - klare Trennung `resume_stream` vs `pause_loop_resume_loop`
  - gleiche Verify-Gates fuer 204/cleanup/idempotenz
- Diese Sektion ist die kanonische Frontend-Quelle bis zur Harmonisierung.

---

### S. SOTA 2026 — Contextual AI Entry Points & Exotic Patterns (Phase 22e)

- [x] **AC87** Kontextueller Chat-Einstieg — beim Oeffnen des Chats von `/trading` wird automatisch injiziert: `"Context: {symbol} · {tf} · {price} · {pct} · Trend: {lineState} SMA50"`; Mechanismus: `useEffect` (false→true Transition) + `setChatContext()` aus `GlobalChatContext`; `buildTradingContext()` in `src/lib/chat-context-builders.ts`; Geo-Seite: FC3 in `frontend_context_delta.md` (ausstehend)
- [x] **AC88** Proaktiver Badge — `badgeCount` in `GlobalChatContext`; Puls-Badge am Bot-Icon wenn `badgeCount > 0 && !chatOpen`; `incrementBadge()` API fuer Market/Geo-Events; `clearBadge()` on chat open; ausstehend: tatsaechliche Trigger (Market-Stream-Anomalie, Geo-Event) verdrahten
- [x] **AC89** Split-View Modus — `ChatMode` (`sheet`|`split`) in `GlobalChatContext`; `SplitChatShell.tsx` rendert Panel neben Content bei `split`; `GlobalChatOverlay` rendert Sheet bei `sheet`; Toggle-Button (Columns2/Square Icon) in `AgentChatToolbar`
- [x] **AC90** "Ask AI about this" Kontextmenue — `AskAiContextMenu.tsx` NEU (shadcn `<ContextMenu>` Radix-Wrapper, `ContextMenuTrigger asChild`, `ContextMenuItem` → `openChat(context)`); `TradingWorkspace.tsx` umgebaut (manuelle `onContextMenu`-Logik entfernt, `<AskAiContextMenu context={askAiContext}>` um Chart-Area); `askAiContext` via `useMemo` (Symbol · Timeframe · OHLCV · Signal · Cross · RVOL); optional `extraItems` Slot fuer GeoMap etc.; `symbol`/`timeframe` Props in `trading/page.tsx` verdrahtet
- [x] **AC91** `@assistant-ui/react` Evaluation — v0.12.17, production-ready, 8.8k Stars. Entscheid: **Nein als Basis-Replacement** (zu opinionated fuer unsere bestehende Komponenten-Struktur), aber **shadcn-Registry-Komponente als Referenz** fuer ToolCallUI + ThreadPrimitive-Patterns. Kein Install noetig.
- [x] **AC92** `vaul` Evaluation — v1.1.2, Maintainer hat "unmaintained" erklaert. Entscheid: **shadcn `<Sheet side="right" modal={false}>`** fuer Chat-Overlay (non-blocking, Chart bleibt interaktiv); shadcn `<Drawer>` (vaul-wrapper) nur bei Bedarf fuer Bottom-Sheet.
- [x] **AC93** AI Copilot Rail — `ChatMode = "sheet" | "split" | "rail"`; `toggleMode` zyklisch (sheet→split→rail→sheet); `SplitChatShell.tsx` rendert 240px Panel wenn `mode === "rail"` unabhaengig von `open` (persistent); `AgentChatToolbar` Icons: Columns2 (sheet→split) / PanelRight (split→rail) / Square (rail→sheet)
- [x] **AC94** Context-Bar im Chat-Header — dismissible emerald Badge in `AgentChatHeader`; zeigt `chatContext` wenn nicht null; X-Button → `clearChatContext()`; Close-Button (X) fuer Sheet via `closeChat()`
- [x] **AC95** `useCompletion` fuer Indikator-Hover-Tooltips — `IndicatorAiTooltip.tsx` NEU (`useCompletion` → `/api/agent/completion`); `/api/agent/completion` NEU (Go-Gateway-Proxy, UIMessage-SSE→plain-text-stream, `claude-haiku-4-5`); `SignalInsightsBar.tsx` — RVOL/CMF/ATR/Rhythm/CompositeSignal Badges mit `IndicatorAiTooltip` gewrappt (`cursor-help`, HoverCard 600ms delay); kein Thread-State, single-shot per Hover; `@ai-sdk/anthropic` bewusst NICHT installiert (provider-agnostisch via Go Gateway)

---

### T. Pause-Loop / Resume-Loop Evaluation (Backend-Orchestrierung)

> Diese Sektion ist bewusst getrennt von Streaming-Stop/Resume.

- [ ] **AC96** Evaluieren: checkpoint-basierte Agent-Loop-Unterbrechung (Workflow/Graph)
- [ ] **AC97** Evaluieren: human approval als Resume-Trigger im Loop (nicht nur Tool-Approval im UI)
- [ ] **AC98** Architekturvorschlag: durable state + idempotente side-effects + replay-safe steps
- [ ] **AC99** Entscheidung dokumentieren: "build now" vs "defer", inkl. Aufwand/Risiko

**Verify-Gates (Sektion T):**

- [ ] **AC.V56** Pause an Schrittgrenze speichert Loop-State reproduzierbar
- [ ] **AC.V57** Resume setzt am letzten Checkpoint fort (kein Full-Rerun)
- [ ] **AC.V58** Side-effects bleiben bei Resume idempotent (kein Double-Write)

**Verify-Gates (Phase 22e):**
- [ ] **AC.V41** Chat oeffnen von `/trading` → Kontext-String automatisch in erster Nachricht sichtbar
- [ ] **AC.V42** Chat oeffnen von `/geopolitical-map` → aktives Event als Kontext injiziert
- [ ] **AC.V43** Proaktiver Badge erscheint bei Stream-Event-Anomalie; verschwindet nach Chat-Oeffnen
- [ ] **AC.V44** Split-View: Toggle im Header wechselt Overlay ↔ Split; Chart in Split-Modus weiterhin interaktiv
- [ ] **AC.V45** Rechtsklick auf Candle → "Ask AI" → Chat oeffnet sich mit Candle-Daten pre-filled
- [ ] **AC.V46** Rechtsklick auf GeoEvent-Marker → "Ask AI" → Chat oeffnet sich mit Event-Daten pre-filled
- [ ] **AC.V47** Kontext-Chip im Chat-Header zeigt aktuellen Kontext; dismiss entfernt Chip

**Verify-Gates (Phase 22f/22g — Rev. 29):**
- [x] **AC.V77** AC51: Paperclip-Button zeigt Count-Badge (orangefarbener Kreis, `{n}`) wenn `attachments.length > 0`; Badge verschwindet nach Senden
- [x] **AC.V78** AC57/58: Assistant-Nachrichten zeigen Sources-Panel wenn `source-url`/`source-document`-Parts vorhanden; max 3 inline, "View N more" oeffnet shadcn Dialog mit allen
- [x] **AC.V79** AC66: Approve/Deny-Buttons im `AgentChatToolBlock` senden `POST /api/agent/approve` mit `{ toolCallId, decision, threadId }`; Callback-Chain vollstaendig (Hook → Panel → Thread → Message → ToolBlock)
- [ ] **AC.V80** AC42: "Regenerate"-Button (RotateCcw) erscheint nur bei letzter Assistant-Nachricht; Klick loest `retry()` aus und ersetzt die Nachricht
- [ ] **AC.V81** AC105: Bearbeitungs-Icon (Pencil) bei User-Nachrichten; Klick oeffnet Inline-Textarea mit vorausgefuelltem Text; "Resend" schneidet History ab Index und sendet neu; "Cancel" schliesst ohne Aenderung
- [ ] **AC.V82** AC90: Rechtsklick auf Candle → Context-Menu mit "Ask AI"-Eintrag; Chat oeffnet sich mit Candle-Prompt vorausgefuellt
- [ ] **AC.V83** AC95: Hover (600ms Delay) auf Indikator-Badge → HoverCard; AI-Completion startet einmalig; Loading-Spinner waehrend Stream; Inhalt wird gecacht (kein erneuter Call)
- [ ] **AC.V84** AC103/104: Token-Badge (`{promptTokens}↑ {completionTokens}↓`) + Kosten-Badge in Message-Footer nach Stream-Ende; Werte kommen aus `message.metadata.promptTokens/completionTokens` (Go muss `messageMetadata`-Event forwarden — siehe ACR-G5)
- [x] **AC.V85** tsc: `bunx tsc --noEmit` 0 Fehler — alle pre-existing Codex-Fehler behoben (`admin/users/route.ts`, `passkeys.ts`, `merge-sqlite.ts`); tsconfig auf ES2022/Next.js-16-SOTA aktualisiert
- [x] **AC.V86** Biome: `bun run lint` 0 Fehler; 4 Warnungen (`noImgElement` fuer blob://-URLs) sind intentional und pre-existing

---

## 3. Evidence Requirements

_(unveraendert aus Rev. 9, plus neu:)_
- Demo: Markdown + Code-Block-Rendering + Copy
- Demo: Speech-Input-Flow (Web Speech API) + TTS-Playback
- Demo: Attachment-Attach + Preview + Send
- Demo: `<think>`-Box collapsed/expanded
- Nachweis: keine Backend-Calls fuer STT/TTS

---

## 4. Propagation Targets

- `docs/specs/EXECUTION_PLAN.md`
- `docs/specs/FRONTEND_ARCHITECTURE.md`
- `docs/specs/execution/frontend_enhancement_delta.md`
- `docs/specs/execution/agent_harness_runtime_delta.md`
- `docs/frontend_chat_ui.md`
- `docs/specs/execution/control_surface_delta.md`
- `docs/specs/execution/command_keyboard_delta.md`

---

### U. Audio / Speech Modalitaet (Phase 22f)

> **Architektur-Ref:** `docs/frontend_chat_ui.md` Sektion 19
> **Backend-Ref:** `agent_chat_runtime_delta.md` Sektion 6 (Audio-Backend)

**Sandwich-Architektur (AI SDK, provider-agnostisch):**
Mic → `transcribe()` → `useChat()` → `generateSpeech()` → AudioContext

- [x] **AC47** Voice-Input via Web Speech API (bereits implementiert — `useSpeechInput`)
- [x] **AC47b** MediaRecorder-Fallback in `AgentChatComposer` — `useMediaRecorderInput` Hook; automatisch aktiv wenn `window.SpeechRecognition` fehlt (Firefox/Safari); sendet Blob an `/api/audio/transcribe`; WebM/Opus MIME-Selection
- [ ] **AC48** Whisper-STT-Pipeline via `transcribe(model, audio)` (AI SDK Core) — ersetzt/ergaenzt Web Speech API Batch-Transkription; Provider: `AGENT_STT_PROVIDER` env var
- [x] **AC48b** `useMicDevices` + Device-Selector in `AgentChatComposer` — `navigator.mediaDevices.enumerateDevices()`; `<select>` neben Mic-Button wenn MediaRecorder-Pfad aktiv + mehr als 1 Device verfuegbar; `deviceId` Constraint an `getUserMedia`
- [ ] **AC48c** Self-hosted STT Integration (WhisperLiveKit) — Python-Backend liefert OpenAI-kompatibles REST; Frontend ruft `transcribe()` mit custom Base-URL
- [x] **AC49b** TTS via BFF `/api/audio/synthesize` + Web Audio API — `AgentChatTtsButton` rewritten; `fetch()` → `arrayBuffer()` → `AudioContext.decodeAudioData()` → `BufferSourceNode.start()`; Loader-Spinner waehrend fetch; Fallback auf Browser SpeechSynthesis bei fetch-Fehler; AbortController fuer sauberes Stop
- [ ] **AC49c** Self-hosted TTS Integration (Kokoro via `kokoro-web`) — OpenAI-API-kompatibel, kein Code-Change noetig

**Verify-Gates Audio:**
- [ ] **AC.V64** Mic-Button → Aufnahme → Transkript erscheint im Composer (Web Speech API Pfad)
- [ ] **AC.V65** Mic-Button → Aufnahme → `transcribe()` → Transkript (Whisper Pfad, braucht Backend)
- [ ] **AC.V66** TTS via `generateSpeech()`: Qualitaet sichtbar besser als Browser SpeechSynthesis
- [ ] **AC.V67** `AGENT_STT_PROVIDER` wechseln (openai → deepgram) ohne Frontend-Code-Aenderung
- [ ] **AC.V68** Self-hosted Kokoro TTS: Audio startet <500ms nach Antwortende

---

### V. Image / Vision Input (Phase 22f)

> **Architektur-Ref:** `docs/frontend_chat_ui.md` Sektion 20

- [x] **AC51b** Eval-Entscheid: Eigenbau via `useAttachments` Hook (`StagedAttachment`+`RequestAttachment`+ObjectURL-Lifecycle); kein SDK-Wrapper noetig — direkte Kontrolle ueber Base64-Encoding + Preview
- [x] **AC51c** Image-Attach-Button — `Paperclip`-Icon in `AgentChatComposer`; hidden `<input type="file" multiple accept="image/*">`; max 5 Dateien / 10MB je Datei; ALLOWED_TYPES-Filter
- [x] **AC52** Staged-Attachment-Preview Strip — `AttachmentPreviewStrip.tsx`; ObjectURL-Thumbnails; Remove-Button; Preview-Klick → `ImagePreviewModal`
- [x] **AC53** Drag & Drop + Clipboard-Paste — impl in `AgentChatComposer`; `isDragging` visual feedback; Clipboard image/paste-items gefiltert
- [x] **AC54** Image-Display in Messages — `AgentChatMessage` rendert Thumbnails fuer User-Messages via `stagedAttachments` prop; Klick → `ImagePreviewModal`
- [x] **AC56** Multi-Modal Image Input — vollstaendiger Stack: `useAttachments.toRequestAttachments()` → BFF Zod-Schema → Go `agentAttachment` struct → Python `_build_user_content()` Anthropic image-blocks + OpenAI `image_url` data-URI

**Verify-Gates Vision:**
- [ ] **AC.V69** Bild per Clipboard paste → Preview-Strip erscheint → Senden → Bild in Message sichtbar
- [ ] **AC.V70** Drag & Drop auf Composer → Preview, kein Page-Reload
- [ ] **AC.V71** Claude Vision: Bild analysieren → Antwort referenziert Bildinhalt korrekt
- [ ] **AC.V72** GPT-4o Vision: gleicher Frontend-Pfad, nur `AGENT_PROVIDER` wechseln

---

### W. Package Additions + Missing Features (Phase 22f)

> **Architektur-Ref:** `docs/frontend_chat_ui.md` Sektion 22

**Pakete:**
- [ ] **AC100** `bun add @assistant-ui/react @assistant-ui/react-ai-sdk` — installieren + in AgentChatPanel verdrahten (DEFERRED — eigene UIMessage-Parts-Pipeline ist SOTA-konform)
- [x] **AC101** `nuqs@2.8.9` installiert — `useQueryState('t')` in `useChatSession` fuer URL-persistente Chat-ID; bei Mount: URL-ID → `chatIdRef`, sonst generieren + in URL schreiben
- [ ] **AC102** `@assistant-ui/react-ai-sdk` Adapter ueber bestehendem `useChat()` Hook — minimale Integrationsflaeche (DEFERRED — kein unmittelbarer Mehrwert gegenueber aktuellem Setup)

**Features die bisher fehlen:**
- [x] **AC103** Token-Usage + Latency Display — `onFinish` captures `{ promptTokens, completionTokens, finishReason }` per messageId in `usageMapRef`; `↑↓`-Badge in `AgentChatMessage` footer (sealed, non-streaming messages); `usageVersion` state counter triggers re-render
- [x] **AC104** Cost-per-Token Anzeige — `COST_PER_TOKEN` Map in `useChatSession` (Sonnet/Opus/Haiku USD/token); `costUsd` in `MessageUsage`; `formatCost()` als `$X.XXXXXX` im Token-Badge; Tooltip zeigt finish-reason + cost
- [x] **AC105** Message Branching — Pencil-Icon auf User-Messages; Inline-Edit Textarea + Resend-Button; `editAndResend(messageId, newText)` in `useChatSession` → `setMessages(slice(0, idx))` + `sendMessage`; kein `@assistant-ui` benoetigt
- [x] **AC106** `rawFinishReason` tracken — in `MessageUsage.finishReason` gespeichert; als Tooltip auf Token-Badge sichtbar; fuer Provider-Debugging verwendbar
- [x] **AC107** Model-Switch mid-conversation — `AgentChatToolbar` controlled (selectedModel/onModelChange props); `useChatSession` exposes `selectedModel`/`setModel`; model in BFF-Request-Body → Go (`agentChatRequestBody.Model`) → Python (`req.model` override `AGENT_MODEL`); History unveraendert

**Interruptible Reasoning Constraint:**
- [x] **AC108** Reasoning-Effort-Control — `ReasoningEffort` type (`low`|`medium`|`high`) in `AgentChatToolbar` als zyklischer Toggle-Button (`BrainCircuit`-Icon + L/M/H Label); `reasoningEffort` + `setReasoningEffort` in `useChatSession`; forwarded in BFF-Body → Go `ReasoningEffort *string` → Python `_REASONING_BUDGET` map → Anthropic `thinking: {type:"enabled", budget_tokens: N}`
- [x] **AC109** Streaming Structured Output + Extended Thinking — Inkompatibilitaet dokumentiert

  **Problem (provider-agnostisch):** Viele LLM-Provider (nicht nur Anthropic) unterstuetzen keine gleichzeitige Verwendung von Structured Output (JSON Schema Enforcement) und Streaming Thinking/Reasoning. Der Grund: Structured Output erfordert das vollstaendige Output-JSON zum Validieren, waehrend Thinking-Tokens vor dem eigentlichen Output generiert werden. Das erzeugt einen fundamentalen Streaming-Kontext-Konflikt.

  **Vercel AI SDK Spezifik:** `streamObject()` + `thinking`-Budget schlaegt mit einem SDK-Fehler fehl (GitHub #12427). Der SDK enforced das Constraint auf API-Ebene nicht.

  **Genereller Workaround (provider-unabhaengig):**
  - Statt `streamObject()` → `streamText()` + `experimental_output` (strukturierter Output als Overlay ueber Text-Stream)
  - Das Thinking laeuft im Text-Stream mit, das strukturierte Resultat wird am Ende aus dem `experimental_output` Channel gelesen
  - Alternativ: zwei separate Requests — erst Thinking-Pass (kein Structured Output), dann Extraction-Pass (Structured Output, kein Thinking)
  - Im Python-Agent: `client.messages.stream()` mit `thinking`-Block + manuellem JSON-Parse des Outputs (kein `response_format`-Parameter gleichzeitig)

  **Wann relevant:** Nur wenn Agent-Antworten gleichzeitig tiefes Reasoning UND ein typisiertes Output-Schema brauchen (z.B. Signal-Extraktion mit Erklaerung). Fuer Standard-Chat-Responses kein Problem — Thinking laeuft normal.

**Stop-Mode / Resume-Mode Entscheid:**
- [x] **AC73a-DECISION** **Stop-Mode ist aktiv** (Phase 22d implementiert via `useChat().stop()`). Resume-Mode als Feature-Flag deferred bis Redis `activeStreamId` Backend-Support gebaut ist (AC73b).

**Verify-Gates:**
- [ ] **AC.V73** Thread-URL per `nuqs`: threadId in URL → neuer Tab oeffnen → gleicher Thread geladen
- [ ] **AC.V74** Token-Badge: erscheint nach Antwort mit Prompt/Completion/Total-Tokens
- [ ] **AC.V75** Message-Branching: Edit vorherige Nachricht → neuer Branch ohne alten Thread zu ueberschreiben
- [ ] **AC.V76** Reasoning-Budget-Toggle: Low vs High sichtbar unterschiedliche Reasoning-Tiefe

