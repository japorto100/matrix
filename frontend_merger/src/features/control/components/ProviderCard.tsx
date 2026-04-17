"use client";

import {
	CheckCircle,
	Cloud,
	DollarSign,
	HardDrive,
	Key,
	Loader2,
	Settings,
	Trash2,
	XCircle,
} from "lucide-react";
import { useState } from "react";
import CurrencyInput from "react-currency-input-field";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import type { ProviderAccountInfo } from "@/lib/queries/control";
import { useSetApiKey, useValidateApiKey } from "@/lib/queries/hooks";
import { cn } from "@/lib/utils";
import type { LlmProvider } from "../types";

const CURRENCIES = ["CHF", "USD", "EUR", "GBP"] as const;
const BUDGET_DURATIONS = [
	{ value: "monthly", label: "Monthly" },
	{ value: "weekly", label: "Weekly" },
	{ value: "daily", label: "Daily" },
] as const;

function formatUsd(val: number | null | undefined): string {
	if (val == null) return "\u2014";
	if (val === 0) return "$0.00";
	if (val < 0.01) return `$${val.toFixed(4)}`;
	if (val < 100) return `$${val.toFixed(2)}`;
	return `$${val.toFixed(0)}`;
}

function AccountInfoBar({ info }: { info: ProviderAccountInfo }) {
	if (info.error) return null;
	const hasCredits = info.limit_remaining != null;
	const hasUsage = info.usage_monthly != null;
	const hasSpend = info.total_spend_usd != null;
	if (!hasCredits && !hasUsage && !hasSpend) return null;

	return (
		<div className="flex items-center gap-2 text-[10px] text-muted-foreground border-t border-border pt-1.5 mt-1.5">
			<DollarSign className="h-3 w-3 shrink-0" />
			{hasCredits && (
				<span>
					Remaining:{" "}
					<span className="text-foreground font-medium">{formatUsd(info.limit_remaining)}</span>
				</span>
			)}
			{hasUsage && (
				<span>
					Month:{" "}
					<span className="text-foreground font-medium">{formatUsd(info.usage_monthly)}</span>
				</span>
			)}
			{hasSpend && info.source === "litellm" && (
				<span>
					Total:{" "}
					<span className="text-foreground font-medium">{formatUsd(info.total_spend_usd)}</span>
				</span>
			)}
			{info.is_free_tier && (
				<Badge variant="secondary" className="text-[8px] h-3.5 px-1 bg-green-500/10 text-green-600">
					Free Tier
				</Badge>
			)}
		</div>
	);
}

export function ProviderCard({
	provider,
	accountInfo,
	onDeleteKey,
	isDeleting,
}: {
	provider: LlmProvider;
	accountInfo?: ProviderAccountInfo;
	onDeleteKey: () => void;
	isDeleting?: boolean;
}) {
	const [settingsOpen, setSettingsOpen] = useState(false);
	const [apiKey, setApiKey] = useState("");
	const [budgetAmount, setBudgetAmount] = useState<string | undefined>(undefined);
	const [budgetCurrency, setBudgetCurrency] = useState("CHF");
	const [budgetDuration, setBudgetDuration] = useState("monthly");
	const [validationResult, setValidationResult] = useState<{
		valid: boolean;
		error?: string;
		models?: string[];
	} | null>(null);

	const validate = useValidateApiKey();
	const saveKey = useSetApiKey();

	const handleTest = async () => {
		if (!apiKey.trim()) return;
		setValidationResult(null);
		try {
			const result = await validate.mutateAsync({
				providerId: provider.id,
				apiKey: apiKey.trim(),
			});
			setValidationResult(result);
		} catch {
			setValidationResult({ valid: false, error: "Request failed" });
		}
	};

	const handleSave = async () => {
		if (!apiKey.trim()) return;
		try {
			const budget = budgetAmount ? Number.parseFloat(budgetAmount) : undefined;
			await saveKey.mutateAsync({
				providerId: provider.id,
				apiKey: apiKey.trim(),
				maxBudget: budget,
				budgetDuration: budget ? budgetDuration : undefined,
				budgetCurrency: budget ? budgetCurrency : undefined,
			});
			toast.success(`${provider.display_name} key saved`);
			setApiKey("");
			setBudgetAmount(undefined);
			setValidationResult(null);
			setSettingsOpen(false);
		} catch {
			toast.error("Failed to save");
		}
	};

	return (
		<Collapsible open={settingsOpen} onOpenChange={setSettingsOpen}>
			<Card
				className={cn(
					"transition-colors",
					provider.is_active && "border-emerald-500/30 bg-emerald-950/5",
				)}
			>
				<CardHeader className="pb-2">
					<div className="flex items-start justify-between gap-2">
						<div className="flex items-center gap-2">
							{provider.type === "cloud" ? (
								<Cloud className="h-3.5 w-3.5 text-sky-400" />
							) : (
								<HardDrive className="h-3.5 w-3.5 text-amber-400" />
							)}
							<CardTitle className="text-sm font-semibold leading-tight">
								{provider.display_name}
							</CardTitle>
						</div>
						<div className="flex items-center gap-1">
							{provider.is_active ? (
								<Badge
									variant="outline"
									className="text-[9px] h-4 px-1.5 border-emerald-500/50 text-emerald-400"
								>
									active
								</Badge>
							) : (
								<Badge variant="outline" className="text-[9px] h-4 px-1.5">
									inactive
								</Badge>
							)}
							<CollapsibleTrigger asChild>
								<Button variant="ghost" size="sm" className="h-6 w-6 p-0">
									<Settings
										className={cn("h-3 w-3 transition-transform", settingsOpen && "rotate-90")}
									/>
								</Button>
							</CollapsibleTrigger>
						</div>
					</div>
				</CardHeader>
				<CardContent className="space-y-2 pt-0">
					{provider.api_key_set && provider.api_key_preview && (
						<div className="flex items-center gap-1.5 text-[11px]">
							<Key className="h-3 w-3 text-muted-foreground" />
							<code className="font-mono text-amber-300">{provider.api_key_preview}</code>
						</div>
					)}
					{provider.available_models.length > 0 && (
						<div className="text-[10px] text-muted-foreground">
							{provider.available_models.length} model
							{provider.available_models.length === 1 ? "" : "s"} available
						</div>
					)}
					{accountInfo && <AccountInfoBar info={accountInfo} />}

					{/* Expandable Settings Panel */}
					<CollapsibleContent>
						<Separator className="my-2" />
						<div className="space-y-3">
							{/* API Key */}
							<div className="space-y-1.5">
								<label className="text-[10px] font-medium uppercase text-muted-foreground">
									API Key
								</label>
								<Input
									type="password"
									placeholder="sk-..."
									value={apiKey}
									onChange={(e) => {
										setApiKey(e.target.value);
										setValidationResult(null);
									}}
									className="h-8 font-mono text-xs"
								/>
							</div>

							{/* Budget */}
							<div className="space-y-1.5">
								<label className="text-[10px] font-medium uppercase text-muted-foreground">
									Budget Limit <span className="font-normal normal-case">(optional)</span>
								</label>
								<div className="flex gap-1.5">
									<Select value={budgetCurrency} onValueChange={setBudgetCurrency}>
										<SelectTrigger className="w-[70px] h-8 text-[10px]">
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											{CURRENCIES.map((c) => (
												<SelectItem key={c} value={c}>
													{c}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
									<CurrencyInput
										className="flex h-8 w-full rounded-md border border-input bg-transparent px-2 py-1 text-xs shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
										placeholder="50.00"
										decimalsLimit={2}
										value={budgetAmount}
										onValueChange={setBudgetAmount}
									/>
									<Select value={budgetDuration} onValueChange={setBudgetDuration}>
										<SelectTrigger className="w-[90px] h-8 text-[10px]">
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											{BUDGET_DURATIONS.map((d) => (
												<SelectItem key={d.value} value={d.value}>
													{d.label}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</div>
							</div>

							{/* Validation Result */}
							{validationResult && (
								<div
									className={cn(
										"flex items-start gap-1.5 rounded border p-2 text-[10px]",
										validationResult.valid
											? "border-emerald-500/30 bg-emerald-950/10 text-emerald-400"
											: "border-red-500/30 bg-red-950/10 text-red-400",
									)}
								>
									{validationResult.valid ? (
										<CheckCircle className="h-3 w-3 mt-0.5 shrink-0" />
									) : (
										<XCircle className="h-3 w-3 mt-0.5 shrink-0" />
									)}
									<span>
										{validationResult.valid
											? `Valid — ${validationResult.models?.length ?? 0} models`
											: (validationResult.error ?? "Invalid")}
									</span>
								</div>
							)}

							{/* Actions */}
							<div className="flex gap-1.5">
								<Button
									variant="outline"
									size="sm"
									className="h-7 text-[10px] gap-1"
									onClick={handleTest}
									disabled={!apiKey.trim() || validate.isPending}
								>
									{validate.isPending ? (
										<Loader2 className="h-2.5 w-2.5 animate-spin" />
									) : (
										<CheckCircle className="h-2.5 w-2.5" />
									)}
									Test
								</Button>
								<Button
									size="sm"
									className="h-7 text-[10px] gap-1"
									onClick={handleSave}
									disabled={!apiKey.trim() || saveKey.isPending}
								>
									{saveKey.isPending ? (
										<Loader2 className="h-2.5 w-2.5 animate-spin" />
									) : (
										<Key className="h-2.5 w-2.5" />
									)}
									Save
								</Button>
								{provider.api_key_set && (
									<Button
										variant="outline"
										size="sm"
										className="h-7 text-[10px] gap-1 text-red-400 hover:text-red-300 ml-auto"
										onClick={onDeleteKey}
										disabled={isDeleting}
									>
										<Trash2 className="h-2.5 w-2.5" />
										Remove
									</Button>
								)}
							</div>
						</div>
					</CollapsibleContent>
				</CardContent>
			</Card>
		</Collapsible>
	);
}
