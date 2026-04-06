"use client";

import {
	Activity,
	Bell,
	BellRing,
	BriefcaseBusiness,
	Check,
	Cpu,
	Globe,
	Plus,
	Trash2,
	TrendingDown,
	TrendingUp,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
	Sheet,
	SheetContent,
	SheetDescription,
	SheetHeader,
	SheetTitle,
	SheetTrigger,
} from "@/components/ui/sheet";
import {
	ALERTS_UPDATED_EVENT,
	clearAllNotifications,
	getAlerts,
	getNotifications,
	getUnreadCount,
	markAllNotificationsRead,
	markNotificationRead,
	notificationKindLabel,
	runAlertVerificationScenario,
	saveAlerts,
} from "./storage";
import type { AlertCondition, AlertNotification, PriceAlert } from "./types";

const CONDITION_LABELS: Record<AlertCondition, string> = {
	above: "Price goes above",
	below: "Price goes below",
	crosses_up: "Price crosses up",
	crosses_down: "Price crosses down",
	rsi_overbought: "RSI above",
	rsi_oversold: "RSI below",
};

function getInitialAlerts(): PriceAlert[] {
	if (typeof window === "undefined") return [];
	return getAlerts();
}

function getInitialNotifications(): AlertNotification[] {
	if (typeof window === "undefined") return [];
	return getNotifications();
}

function getInitialUnreadCount(): number {
	if (typeof window === "undefined") return 0;
	return getUnreadCount();
}

const PROFILE_KEY = "default";

export function AlertPanel() {
	const router = useRouter();
	const [alerts, setAlerts] = useState<PriceAlert[]>(getInitialAlerts);
	const [notifications, setNotifications] = useState<AlertNotification[]>(getInitialNotifications);
	const [unreadCount, setUnreadCount] = useState(getInitialUnreadCount);
	const [showCreate, setShowCreate] = useState(false);
	const [verificationStatus, setVerificationStatus] = useState<string | null>(null);
	const [loadError, setLoadError] = useState<string | null>(null);
	const [newAlert, setNewAlert] = useState({
		symbol: "BTC/USD",
		condition: "above" as AlertCondition,
		targetValue: "",
		message: "",
	});

	const loadAlertsFromApi = useCallback(async () => {
		try {
			const response = await fetch(
				`/api/fusion/alerts?profileKey=${encodeURIComponent(PROFILE_KEY)}`,
				{ cache: "no-store" },
			);
			if (!response.ok) throw new Error(`alerts fetch failed (${response.status})`);
			const payload = (await response.json()) as { alerts?: PriceAlert[] };
			const nextAlerts = Array.isArray(payload.alerts) ? payload.alerts : [];
			setAlerts(nextAlerts);
			saveAlerts(nextAlerts);
			setLoadError(null);
			return;
		} catch (error) {
			setLoadError(error instanceof Error ? error.message : "Alert inbox sync failed.");
			setAlerts(getAlerts());
		}
	}, []);

	const refreshFromStorage = useCallback(() => {
		setNotifications(getNotifications());
		setUnreadCount(getUnreadCount());
	}, []);

	useEffect(() => {
		void loadAlertsFromApi();
	}, [loadAlertsFromApi]);

	useEffect(() => {
		const handleAlertsUpdate = () => refreshFromStorage();
		const handleStorage = (event: StorageEvent) => {
			if (event.key === "tradeview_alerts" || event.key === "tradeview_notifications") {
				refreshFromStorage();
			}
		};

		window.addEventListener(ALERTS_UPDATED_EVENT, handleAlertsUpdate as EventListener);
		window.addEventListener("storage", handleStorage);

		return () => {
			window.removeEventListener(ALERTS_UPDATED_EVENT, handleAlertsUpdate as EventListener);
			window.removeEventListener("storage", handleStorage);
		};
	}, [refreshFromStorage]);

	const handleCreateAlert = async () => {
		const targetValue = parseFloat(newAlert.targetValue);
		if (Number.isNaN(targetValue)) return;

		const response = await fetch("/api/fusion/alerts", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({
				profileKey: PROFILE_KEY,
				symbol: newAlert.symbol,
				condition: newAlert.condition,
				targetValue,
				message: newAlert.message || undefined,
			}),
		});
		if (!response.ok) {
			return;
		}
		await loadAlertsFromApi();
		setShowCreate(false);
		setNewAlert({
			symbol: "BTC/USD",
			condition: "above",
			targetValue: "",
			message: "",
		});
	};

	const handleDeleteAlert = async (id: string) => {
		const response = await fetch(
			`/api/fusion/alerts/${encodeURIComponent(id)}?profileKey=${encodeURIComponent(PROFILE_KEY)}`,
			{ method: "DELETE" },
		);
		if (!response.ok) {
			return;
		}
		await loadAlertsFromApi();
	};

	const handleToggleAlert = async (id: string, enabled: boolean) => {
		const response = await fetch(`/api/fusion/alerts/${encodeURIComponent(id)}`, {
			method: "PATCH",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({
				profileKey: PROFILE_KEY,
				enabled,
			}),
		});
		if (!response.ok) {
			return;
		}
		await loadAlertsFromApi();
	};

	const handleMarkRead = (id: string) => {
		markNotificationRead(id);
		setNotifications(getNotifications());
		setUnreadCount(getUnreadCount());
	};

	const handleOpenNotification = (notification: AlertNotification) => {
		handleMarkRead(notification.id);
		router.push(notification.targetHref);
	};

	const handleMarkAllRead = () => {
		markAllNotificationsRead();
		setNotifications(getNotifications());
		setUnreadCount(0);
	};

	const handleClearNotifications = () => {
		clearAllNotifications();
		setNotifications([]);
		setUnreadCount(0);
	};

	const handleRunVerification = () => {
		const result = runAlertVerificationScenario("BTC/USD");
		if (result.passed) {
			setVerificationStatus("Self-check passed: above=1, below=1, duplicate=0");
		} else {
			setVerificationStatus(`Self-check failed: ${result.notes.join("; ") || "unexpected result"}`);
		}
		refreshFromStorage();
	};

	const notificationIcon = (notification: AlertNotification) => {
		switch (notification.kind) {
			case "event":
				return <BellRing className="h-3 w-3 text-sky-400" />;
			case "portfolio":
				return <BriefcaseBusiness className="h-3 w-3 text-emerald-400" />;
			case "geopolitical":
				return <Globe className="h-3 w-3 text-amber-300" />;
			case "system":
				return <Cpu className="h-3 w-3 text-violet-400" />;
			default:
				return <Bell className="h-3 w-3 text-muted-foreground" />;
		}
	};

	return (
		<Sheet>
			<SheetTrigger asChild>
				<Button variant="ghost" size="icon" className="h-9 w-9 relative">
					{unreadCount > 0 ? <BellRing className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
					<span className="sr-only">
						{unreadCount > 0
							? `Open alerts and notifications, ${unreadCount} unread`
							: "Open alerts and notifications"}
					</span>
					{unreadCount > 0 && (
						<span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-status-error text-[10px] font-semibold text-white">
							{unreadCount > 9 ? "9+" : unreadCount}
						</span>
					)}
				</Button>
			</SheetTrigger>
			<SheetContent className="w-[400px] sm:max-w-[400px]">
				<SheetHeader>
					<SheetTitle className="flex items-center gap-2">
						<Bell className="h-5 w-5" />
						Alerts & Notifications
					</SheetTitle>
					<SheetDescription>Manage price alerts and view notifications</SheetDescription>
				</SheetHeader>

				<div className="mt-6 space-y-6">
					<div>
						<div className="flex items-center justify-between mb-3">
							<h3 className="text-sm font-medium">Notifications</h3>
							<div className="flex gap-2">
								<Button variant="ghost" size="sm" onClick={handleRunVerification}>
									Self-check
								</Button>
								<Button
									variant="ghost"
									size="sm"
									onClick={handleMarkAllRead}
									disabled={unreadCount === 0}
								>
									<Check className="h-3 w-3 mr-1" />
									Mark all read
								</Button>
								<Button
									variant="ghost"
									size="sm"
									onClick={handleClearNotifications}
									disabled={notifications.length === 0}
								>
									<Trash2 className="h-3 w-3 mr-1" />
									Clear
								</Button>
							</div>
						</div>
						{verificationStatus && (
							<div className="mb-2 text-[11px] text-muted-foreground">{verificationStatus}</div>
						)}
						{loadError ? (
							<div className="mb-2 text-[11px] text-status-warning">{loadError}</div>
						) : null}

						<ScrollArea className="h-[200px]">
							{notifications.length === 0 ? (
								<div className="text-center py-8 text-muted-foreground text-sm">
									No notifications
								</div>
							) : (
								<div className="space-y-2">
									{notifications
										.slice()
										.reverse()
										.map((notification) => (
											<div
												key={notification.id}
												role="button"
												tabIndex={0}
												onClick={() => handleOpenNotification(notification)}
												onKeyDown={(event) => {
													if (event.key === "Enter" || event.key === " ") {
														event.preventDefault();
														handleOpenNotification(notification);
													}
												}}
												className={`w-full p-3 rounded-lg border border-border text-left transition-colors hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40 ${
													notification.read ? "bg-card/30" : "bg-card/70"
												}`}
												aria-label={`Open ${notificationKindLabel(notification.kind)} notification for ${notification.symbol}`}
											>
												<div className="flex items-start justify-between">
													<div>
														<div className="flex items-center gap-2">
															{notificationIcon(notification)}
															<div className="font-medium text-sm">{notification.symbol}</div>
															<Badge variant="outline" className="text-[10px] uppercase">
																{notificationKindLabel(notification.kind)}
															</Badge>
														</div>
														<div className="text-xs text-muted-foreground mt-1">
															<span className="sr-only">Notification message: </span>
															{notification.message}
														</div>
														<div className="text-xs text-muted-foreground mt-1">
															{new Date(notification.timestamp).toLocaleString()}
														</div>
													</div>
													{!notification.read && (
														<Button
															variant="ghost"
															size="sm"
															onClick={(event) => {
																event.stopPropagation();
																handleMarkRead(notification.id);
															}}
														>
															<Check className="h-3 w-3" />
														</Button>
													)}
												</div>
											</div>
										))}
								</div>
							)}
						</ScrollArea>
					</div>

					<Separator />

					<div>
						<div className="flex items-center justify-between mb-3">
							<h3 className="text-sm font-medium">Price Alerts</h3>
							<Dialog open={showCreate} onOpenChange={setShowCreate}>
								<DialogTrigger asChild>
									<Button size="sm">
										<Plus className="h-3 w-3 mr-1" />
										New Alert
									</Button>
								</DialogTrigger>
								<DialogContent>
									<DialogHeader>
										<DialogTitle>Create Price Alert</DialogTitle>
										<DialogDescription>
											Get notified when price reaches your target
										</DialogDescription>
									</DialogHeader>
									<div className="space-y-4 mt-4">
										<div className="space-y-2">
											<Label>Symbol</Label>
											<Input
												placeholder="BTC/USD"
												value={newAlert.symbol}
												onChange={(event) =>
													setNewAlert({ ...newAlert, symbol: event.target.value })
												}
											/>
										</div>
										<div className="space-y-2">
											<Label>Condition</Label>
											<Select
												value={newAlert.condition}
												onValueChange={(value) =>
													setNewAlert({ ...newAlert, condition: value as AlertCondition })
												}
											>
												<SelectTrigger>
													<SelectValue />
												</SelectTrigger>
												<SelectContent>
													{Object.entries(CONDITION_LABELS).map(([value, label]) => (
														<SelectItem key={value} value={value}>
															{label}
														</SelectItem>
													))}
												</SelectContent>
											</Select>
										</div>
										<div className="space-y-2">
											<Label>Target Value</Label>
											<Input
												type="number"
												placeholder="70000"
												value={newAlert.targetValue}
												onChange={(event) =>
													setNewAlert({ ...newAlert, targetValue: event.target.value })
												}
											/>
										</div>
										<div className="space-y-2">
											<Label>Message (optional)</Label>
											<Input
												placeholder="Custom alert message"
												value={newAlert.message}
												onChange={(event) =>
													setNewAlert({ ...newAlert, message: event.target.value })
												}
											/>
										</div>
										<Button onClick={handleCreateAlert} className="w-full">
											Create Alert
										</Button>
									</div>
								</DialogContent>
							</Dialog>
						</div>

						<ScrollArea className="h-[250px]">
							{alerts.length === 0 ? (
								<div className="text-center py-8 text-muted-foreground text-sm">
									No alerts configured
								</div>
							) : (
								<div className="space-y-2">
									{alerts.map((alert) => (
										<div
											key={alert.id}
											className={`p-3 rounded-lg border border-border ${
												alert.triggered ? "border-warning/50 bg-warning/10" : "bg-card/50"
											}`}
										>
											<div className="flex items-center justify-between">
												<div>
													<div className="flex items-center gap-2">
														<span className="font-medium text-sm">{alert.symbol}</span>
														{alert.triggered ? (
															<Badge
																variant="outline"
																className="border-warning/50 text-xs text-status-warning"
															>
																Triggered
															</Badge>
														) : null}
													</div>
													<div className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
														{alert.condition.includes("above") ||
														alert.condition === "crosses_up" ? (
															<TrendingUp className="h-3 w-3 text-status-success" />
														) : alert.condition.includes("below") ||
															alert.condition === "crosses_down" ? (
															<TrendingDown className="h-3 w-3 text-status-error" />
														) : (
															<Activity className="h-3 w-3 text-status-info" />
														)}
														{CONDITION_LABELS[alert.condition]} {alert.targetValue}
													</div>
												</div>
												<div className="flex items-center gap-1">
													<Button
														variant="ghost"
														size="sm"
														onClick={() => handleToggleAlert(alert.id, !alert.enabled)}
													>
														{alert.enabled ? (
															<Bell className="h-3 w-3" />
														) : (
															<BellOff className="h-3 w-3 text-muted-foreground" />
														)}
													</Button>
													<Button
														variant="ghost"
														size="sm"
														onClick={() => handleDeleteAlert(alert.id)}
													>
														<Trash2 className="h-3 w-3 text-status-error" />
													</Button>
												</div>
											</div>
										</div>
									))}
								</div>
							)}
						</ScrollArea>
					</div>
				</div>
			</SheetContent>
		</Sheet>
	);
}

function BellOff({ className }: { className?: string }) {
	return (
		<svg
			xmlns="http://www.w3.org/2000/svg"
			width="24"
			height="24"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth="2"
			strokeLinecap="round"
			strokeLinejoin="round"
			className={className}
		>
			<path d="M10.268 21a2 2 0 0 0 3.464 0" />
			<path d="M3.262 15.326A1 1 0 0 0 4.26 17h14.016a1 1 0 0 0 .998-1.674L13.49 5.083a1 1 0 0 0-1.98 0L3.262 15.326z" />
			<line x1="2" y1="2" x2="22" y2="22" />
		</svg>
	);
}
