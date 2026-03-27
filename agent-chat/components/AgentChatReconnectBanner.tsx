"use client";

// AC72: Reconnect/degraded banner — separate from error banner
// States: reconnecting (spinner) | degraded (polling) | recovered (green, auto-dismiss)

import { CheckCircle, Loader2, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";

export type StreamStatus = "live" | "reconnecting" | "degraded" | "recovered";

interface AgentChatReconnectBannerProps {
	status: StreamStatus;
}

export function AgentChatReconnectBanner({ status }: AgentChatReconnectBannerProps) {
	const [visible, setVisible] = useState(false);

	useEffect(() => {
		if (status === "live") {
			setVisible(false);
			return;
		}
		setVisible(true);
		if (status === "recovered") {
			const t = setTimeout(() => setVisible(false), 2500);
			return () => clearTimeout(t);
		}
	}, [status]);

	if (!visible) return null;

	const config = {
		reconnecting: {
			icon: <Loader2 className="h-3 w-3 animate-spin" />,
			label: "Reconnecting…",
			cls: "border-amber-500/30 bg-amber-500/10 text-amber-400",
		},
		degraded: {
			icon: <WifiOff className="h-3 w-3" />,
			label: "Connection degraded — polling fallback active",
			cls: "border-orange-500/30 bg-orange-500/10 text-orange-400",
		},
		recovered: {
			icon: <CheckCircle className="h-3 w-3" />,
			label: "Connection restored",
			cls: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
		},
		live: { icon: null, label: "", cls: "" },
	} as const;

	const { icon, label, cls } = config[status];

	return (
		<div
			className={`mx-3 mb-1 flex items-center gap-2 rounded border px-3 py-1 text-[11px] shrink-0 ${cls}`}
		>
			{icon}
			<span>{label}</span>
		</div>
	);
}
