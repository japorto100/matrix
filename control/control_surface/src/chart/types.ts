// Chart Engine Types
export type ChartType = "candlestick" | "line" | "area" | "heikinashi" | "hollow";
export type ScaleType = "linear" | "logarithmic";

export interface Viewport {
	width: number;
	height: number;
	offsetX: number;
	offsetY: number;
	scale: number;
	minPrice: number;
	maxPrice: number;
	startIndex: number;
	endIndex: number;
	candleWidth: number;
	candleSpacing: number;
}

export interface ChartConfig {
	chartType: ChartType;
	scaleType: ScaleType;
	showVolume: boolean;
	showGrid: boolean;
	showCrosshair: boolean;
	showOHLC: boolean;
	showWatermark: boolean;
	backgroundColor: string;
	gridColor: string;
	textColor: string;
	upColor: string;
	downColor: string;
	volumeUpColor: string;
	volumeDownColor: string;
	crosshairColor: string;
	crosshairStyle: "solid" | "dashed" | "dotted";
}

export interface Candle {
	time: number;
	open: number;
	high: number;
	low: number;
	close: number;
	volume: number;
	// Derived
	isUp?: boolean;
	bodyTop?: number;
	bodyBottom?: number;
	bodyHeight?: number;
	wickTop?: number;
	wickBottom?: number;
}

export interface Indicator {
	id: string;
	name: string;
	type: string;
	enabled: boolean;
	visible: boolean;
	data: IndicatorPoint[];
	config: Record<string, unknown>;
	color: string;
	lineWidth: number;
	lineStyle: "solid" | "dashed" | "dotted";
}

export interface IndicatorPoint {
	time: number;
	value: number;
}

export interface Drawing {
	id: string;
	type: DrawingType;
	points: DrawingPoint[];
	color: string;
	lineWidth: number;
	lineStyle: "solid" | "dashed" | "dotted";
	visible: boolean;
	locked: boolean;
	text?: string;
	config?: Record<string, unknown>;
}

export type DrawingType =
	| "trendline"
	| "horizontalline"
	| "verticalline"
	| "rectangle"
	| "fibonacci"
	| "fibextension"
	| "pitchfork"
	| "text"
	| "measure"
	| "arrow"
	| "circle";

export interface DrawingPoint {
	time: number;
	price: number;
	x?: number;
	y?: number;
}

export interface ChartState {
	symbol: string;
	timeframe: string;
	candles: Candle[];
	viewport: Viewport;
	config: ChartConfig;
	indicators: Indicator[];
	drawings: Drawing[];
	crosshair: CrosshairState | null;
	isLoading: boolean;
	error: string | null;
	sessionId: string;
}

export interface CrosshairState {
	time: number;
	price: number;
	x: number;
	y: number;
	candleIndex: number;
	visible: boolean;
}

export interface ChartTheme {
	name: string;
	background: string;
	backgroundGradient?: [string, string];
	grid: string;
	text: string;
	textMuted: string;
	up: string;
	down: string;
	volumeUp: string;
	volumeDown: string;
	crosshair: string;
	indicator: {
		sma: string;
		ema: string;
		bollinger: string;
		macd: string;
		signal: string;
		histogram: string;
		rsi: string;
	};
}

// Default Themes
export const THEMES: Record<string, ChartTheme> = {
	dark: {
		name: "Dark",
		background: "#0f172a",
		backgroundGradient: ["#0f172a", "#1e293b"],
		grid: "#1e293b",
		text: "#94a3b8",
		textMuted: "#64748b",
		up: "#22c55e",
		down: "#ef4444",
		volumeUp: "rgba(34, 197, 94, 0.4)",
		volumeDown: "rgba(239, 68, 68, 0.4)",
		crosshair: "#3b82f6",
		indicator: {
			sma: "#3b82f6",
			ema: "#f59e0b",
			bollinger: "#8b5cf6",
			macd: "#06b6d4",
			signal: "#f43f5e",
			histogram: "#6366f1",
			rsi: "#a855f7",
		},
	},
	light: {
		name: "Light",
		background: "#ffffff",
		grid: "#e2e8f0",
		text: "#475569",
		textMuted: "#94a3b8",
		up: "#16a34a",
		down: "#dc2626",
		volumeUp: "rgba(22, 163, 74, 0.4)",
		volumeDown: "rgba(220, 38, 38, 0.4)",
		crosshair: "#2563eb",
		indicator: {
			sma: "#2563eb",
			ema: "#d97706",
			bollinger: "#7c3aed",
			macd: "#0891b2",
			signal: "#e11d48",
			histogram: "#4f46e5",
			rsi: "#9333ea",
		},
	},
};

// Timeframe Configurations
export interface TimeframeConfig {
	value: string;
	label: string;
	ms: number;
	format: string;
	group: "intraday" | "day" | "week" | "month";
}

export const TIMEFRAMES: TimeframeConfig[] = [
	{ value: "1", label: "1m", ms: 60000, format: "HH:mm", group: "intraday" },
	{ value: "3", label: "3m", ms: 180000, format: "HH:mm", group: "intraday" },
	{ value: "5", label: "5m", ms: 300000, format: "HH:mm", group: "intraday" },
	{ value: "15", label: "15m", ms: 900000, format: "HH:mm", group: "intraday" },
	{ value: "30", label: "30m", ms: 1800000, format: "HH:mm", group: "intraday" },
	{ value: "60", label: "1H", ms: 3600000, format: "HH:mm", group: "intraday" },
	{ value: "120", label: "2H", ms: 7200000, format: "HH:mm", group: "intraday" },
	{ value: "240", label: "4H", ms: 14400000, format: "HH:mm", group: "intraday" },
	{ value: "D", label: "1D", ms: 86400000, format: "MMM dd", group: "day" },
	{ value: "W", label: "1W", ms: 604800000, format: "MMM dd", group: "week" },
	{ value: "M", label: "1M", ms: 2592000000, format: "MMM yyyy", group: "month" },
];
