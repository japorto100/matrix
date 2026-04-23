"use client";

// ADR-001 G6 — Smart-Routing Control-UI Panel
// Lets users opt into cheap-vs-strong routing, configure the cheap model,
// and tune the simple-turn thresholds. Backend: /api/v1/control/user/llm/smart-routing.
// GDPR-relevant: enabling this means silent model substitution — the
// disclosure text makes the behaviour explicit before the toggle.

import { AlertTriangle, Loader2, Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

interface SmartRoutingConfig {
	enabled?: boolean;
	cheap_model?: string;
	max_simple_chars?: number;
	max_simple_words?: number;
}

interface FetchedResponse {
	user_id?: string;
	smart_routing?: SmartRoutingConfig;
}

const DEFAULT_MAX_CHARS = 160;
const DEFAULT_MAX_WORDS = 28;

export function SmartRoutingSection() {
	const [cfg, setCfg] = useState<SmartRoutingConfig>({});
	const [loading, setLoading] = useState(true);
	const [saving, setSaving] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [savedAt, setSavedAt] = useState<number | null>(null);

	const load = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const res = await fetch("/api/control/user/llm/smart-routing", {
				headers: { accept: "application/json" },
			});
			if (!res.ok) {
				throw new Error(`HTTP ${res.status}`);
			}
			const data: FetchedResponse = await res.json();
			setCfg(data.smart_routing ?? {});
		} catch (e) {
			setError(e instanceof Error ? e.message : "load failed");
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		void load();
	}, [load]);

	const save = useCallback(async () => {
		setSaving(true);
		setError(null);
		try {
			const payload: SmartRoutingConfig = cfg.enabled
				? {
						enabled: true,
						cheap_model: cfg.cheap_model?.trim() || "",
						max_simple_chars: cfg.max_simple_chars ?? DEFAULT_MAX_CHARS,
						max_simple_words: cfg.max_simple_words ?? DEFAULT_MAX_WORDS,
					}
				: { enabled: false };
			const res = await fetch("/api/control/user/llm/smart-routing", {
				method: "PUT",
				headers: { "content-type": "application/json" },
				body: JSON.stringify(payload),
			});
			if (!res.ok) {
				throw new Error(`HTTP ${res.status}`);
			}
			const data: { smart_routing?: SmartRoutingConfig } = await res.json();
			setCfg(data.smart_routing ?? {});
			setSavedAt(Date.now());
		} catch (e) {
			setError(e instanceof Error ? e.message : "save failed");
		} finally {
			setSaving(false);
		}
	}, [cfg]);

	const enabled = Boolean(cfg.enabled);
	const cheapInvalid = enabled && (!cfg.cheap_model || cfg.cheap_model.trim() === "");

	return (
		<Card>
			<CardHeader className="pb-3">
				<div className="flex items-start justify-between gap-3">
					<div>
						<CardTitle className="text-sm font-semibold flex items-center gap-1.5">
							<Zap className="h-3.5 w-3.5" />
							Smart Routing
							{enabled ? (
								<Badge
									variant="outline"
									className="text-[9px] h-4 px-1.5 border-amber-500/50 text-amber-500"
								>
									active
								</Badge>
							) : (
								<Badge variant="outline" className="text-[9px] h-4 px-1.5">
									disabled
								</Badge>
							)}
						</CardTitle>
						<p className="mt-1 text-[11px] text-muted-foreground leading-relaxed">
							When a first-turn message looks clearly simple (short, no code, no URLs, no domain
							keywords), route it to a cheap model instead of your primary. Saves cost for trivia;
							your primary model still answers anything complex.
						</p>
					</div>
					<Switch
						checked={enabled}
						onCheckedChange={(v) => setCfg((prev) => ({ ...prev, enabled: Boolean(v) }))}
						disabled={loading || saving}
						aria-label="Enable smart routing"
					/>
				</div>
			</CardHeader>
			<CardContent className="space-y-3 pt-0">
				{enabled && (
					<>
						<div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-2.5 text-[10px] leading-relaxed text-amber-700 dark:text-amber-400">
							<div className="flex items-start gap-1.5">
								<AlertTriangle className="h-3 w-3 mt-0.5 flex-shrink-0" />
								<div>
									<strong>Disclosure:</strong> When enabled, simple first-turn messages will be
									answered by the cheap model shown below — <em>not</em> your primary. Every
									cheap-routed reply is flagged in the chat with a "cheap-routed" badge.
									Tool-continuation turns always use your primary.
								</div>
							</div>
						</div>

						<div className="space-y-1.5">
							<Label htmlFor="smart-routing-cheap-model" className="text-[11px]">
								Cheap model ID
							</Label>
							<Input
								id="smart-routing-cheap-model"
								value={cfg.cheap_model ?? ""}
								onChange={(e) => setCfg((prev) => ({ ...prev, cheap_model: e.target.value }))}
								placeholder="e.g. openai/gpt-4o-mini or anthropic/claude-haiku-4-5"
								className="font-mono text-xs h-8"
								disabled={loading || saving}
								aria-invalid={cheapInvalid}
							/>
							{cheapInvalid && (
								<p className="text-[10px] text-red-500">Required when smart-routing is enabled.</p>
							)}
							<p className="text-[10px] text-muted-foreground">
								Must be a model the LiteLLM gateway can resolve. Ideally same vendor as your primary
								(skips the credential pre-flight overhead).
							</p>
						</div>

						<div className="grid grid-cols-2 gap-3">
							<div className="space-y-1.5">
								<Label htmlFor="smart-routing-max-chars" className="text-[11px]">
									Max chars for "simple"
								</Label>
								<Input
									id="smart-routing-max-chars"
									type="number"
									min={20}
									max={2000}
									value={cfg.max_simple_chars ?? DEFAULT_MAX_CHARS}
									onChange={(e) =>
										setCfg((prev) => ({
											...prev,
											max_simple_chars: Number.parseInt(e.target.value, 10) || undefined,
										}))
									}
									className="font-mono text-xs h-8"
									disabled={loading || saving}
								/>
								<p className="text-[10px] text-muted-foreground">
									Default {DEFAULT_MAX_CHARS}. Longer messages always stay on primary.
								</p>
							</div>
							<div className="space-y-1.5">
								<Label htmlFor="smart-routing-max-words" className="text-[11px]">
									Max words for "simple"
								</Label>
								<Input
									id="smart-routing-max-words"
									type="number"
									min={3}
									max={500}
									value={cfg.max_simple_words ?? DEFAULT_MAX_WORDS}
									onChange={(e) =>
										setCfg((prev) => ({
											...prev,
											max_simple_words: Number.parseInt(e.target.value, 10) || undefined,
										}))
									}
									className="font-mono text-xs h-8"
									disabled={loading || saving}
								/>
								<p className="text-[10px] text-muted-foreground">
									Default {DEFAULT_MAX_WORDS}. Combined AND with char limit.
								</p>
							</div>
						</div>
					</>
				)}

				<div className="flex items-center justify-between pt-1">
					<div className="text-[10px] text-muted-foreground">
						{loading && (
							<span className="inline-flex items-center gap-1">
								<Loader2 className="h-2.5 w-2.5 animate-spin" /> loading…
							</span>
						)}
						{!loading && error && <span className="text-red-500">error: {error}</span>}
						{!loading && !error && savedAt && (
							<span className="text-emerald-600">
								saved {new Date(savedAt).toLocaleTimeString()}
							</span>
						)}
					</div>
					<Button
						size="sm"
						onClick={() => void save()}
						disabled={loading || saving || (enabled && cheapInvalid)}
						className="h-7 text-xs"
					>
						{saving ? (
							<>
								<Loader2 className="h-3 w-3 mr-1 animate-spin" /> saving…
							</>
						) : (
							"Save"
						)}
					</Button>
				</div>
			</CardContent>
		</Card>
	);
}
