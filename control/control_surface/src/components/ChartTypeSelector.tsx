"use client";

import { AreaChart, BarChart3, ChevronDown, LineChart } from "lucide-react";
import type { ChartType } from "@/chart/types";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ChartTypeSelectorProps {
	chartType: ChartType;
	onChartTypeChange: (type: ChartType) => void;
}

const CHART_TYPES: Array<{ type: ChartType; label: string; icon: React.ReactNode }> = [
	{ type: "candlestick", label: "Candlestick", icon: <BarChart3 className="h-4 w-4" /> },
	{ type: "line", label: "Line", icon: <LineChart className="h-4 w-4" /> },
	{ type: "area", label: "Area", icon: <AreaChart className="h-4 w-4" /> },
	{
		type: "heikinashi",
		label: "Heikin Ashi",
		icon: <BarChart3 className="h-4 w-4 text-purple-500" />,
	},
	{
		type: "hollow",
		label: "Hollow Candles",
		icon: <BarChart3 className="h-4 w-4 text-amber-500" />,
	},
];

export function ChartTypeSelector({ chartType, onChartTypeChange }: ChartTypeSelectorProps) {
	const currentChart = CHART_TYPES.find((c) => c.type === chartType) ?? CHART_TYPES[0];
	if (!currentChart) return null;

	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>
				<Button variant="outline" size="sm" className="gap-2">
					{currentChart.icon}
					<span className="hidden sm:inline">{currentChart.label}</span>
					<ChevronDown className="h-3 w-3" />
				</Button>
			</DropdownMenuTrigger>
			<DropdownMenuContent align="end">
				{CHART_TYPES.map((ct) => (
					<DropdownMenuItem
						key={ct.type}
						onClick={() => onChartTypeChange(ct.type)}
						className={chartType === ct.type ? "bg-accent" : ""}
					>
						<span className="mr-2">{ct.icon}</span>
						{ct.label}
					</DropdownMenuItem>
				))}
			</DropdownMenuContent>
		</DropdownMenu>
	);
}

export default ChartTypeSelector;
