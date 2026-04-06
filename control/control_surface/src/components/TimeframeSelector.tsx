"use client";

import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { TimeframeValue } from "@/lib/providers/types";

const TIMEFRAMES: Array<{ value: TimeframeValue; label: string }> = [
	{ value: "1m", label: "1m" },
	{ value: "3m", label: "3m" },
	{ value: "5m", label: "5m" },
	{ value: "15m", label: "15m" },
	{ value: "30m", label: "30m" },
	{ value: "1H", label: "1H" },
	{ value: "2H", label: "2H" },
	{ value: "4H", label: "4H" },
	{ value: "1D", label: "1D" },
	{ value: "1W", label: "1W" },
	{ value: "1M", label: "1M" },
];

interface TimeframeSelectorProps {
	currentTimeframe: TimeframeValue;
	onTimeframeChange: (timeframe: TimeframeValue) => void;
}

export function TimeframeSelector({ currentTimeframe, onTimeframeChange }: TimeframeSelectorProps) {
	return (
		<ToggleGroup
			type="single"
			value={currentTimeframe}
			onValueChange={(value) => {
				if (value) onTimeframeChange(value as TimeframeValue);
			}}
			className="bg-background/50 border border-border rounded-lg p-1 gap-0.5"
		>
			{TIMEFRAMES.map((tf) => (
				<ToggleGroupItem
					key={tf.value}
					value={tf.value}
					aria-label={tf.label}
					data-testid={`timeframe-${tf.value}`}
					className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
						currentTimeframe === tf.value
							? "bg-emerald-500 text-white hover:bg-emerald-600"
							: "hover:bg-accent"
					}`}
				>
					{tf.label}
				</ToggleGroupItem>
			))}
		</ToggleGroup>
	);
}
