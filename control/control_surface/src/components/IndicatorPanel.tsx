"use client";

import { LineChart } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";

export interface IndicatorSettings {
	sma: { enabled: boolean; period: number };
	ema: { enabled: boolean; period: number };
	rsi: { enabled: boolean; period: number };
	macd?: { enabled: boolean };
	bollinger?: { enabled: boolean; period: number; stdDev: number };
	vwap?: { enabled: boolean };
	vwma?: { enabled: boolean; period: number };
	atr?: { enabled: boolean; period: number };
	atrChannel?: { enabled: boolean; smaPeriod: number; atrPeriod: number; multiplier: number };
	hma?: { enabled: boolean; period: number };
	adx?: { enabled: boolean; period: number };
	ichimoku?: {
		enabled: boolean;
		tenkanPeriod: number;
		kijunPeriod: number;
		senkouBPeriod: number;
		displacement: number;
	};
	parabolicSar?: { enabled: boolean; step: number; maxAF: number };
	keltner?: { enabled: boolean; emaPeriod: number; atrPeriod: number; multiplier: number };
	volumeProfile?: { enabled: boolean; levels: number; topN: number };
	supportResistance?: { enabled: boolean; lookback: number; threshold: number; topN: number };
}

interface IndicatorPanelProps {
	indicators: IndicatorSettings;
	onIndicatorsChange: (indicators: IndicatorSettings) => void;
}

const PERIOD_OPTIONS = [5, 10, 20, 50, 100, 200];

export function IndicatorPanel({ indicators, onIndicatorsChange }: IndicatorPanelProps) {
	const updateIndicator = (
		indicator: keyof IndicatorSettings,
		field: string,
		value: boolean | number,
	) => {
		onIndicatorsChange({
			...indicators,
			[indicator]: {
				...indicators[indicator],
				[field]: value,
			},
		});
	};

	const activeIndicatorsCount =
		(indicators.sma.enabled ? 1 : 0) +
		(indicators.ema.enabled ? 1 : 0) +
		(indicators.rsi.enabled ? 1 : 0) +
		(indicators.macd?.enabled ? 1 : 0) +
		(indicators.bollinger?.enabled ? 1 : 0) +
		(indicators.vwap?.enabled ? 1 : 0) +
		(indicators.vwma?.enabled ? 1 : 0) +
		(indicators.atr?.enabled ? 1 : 0) +
		(indicators.atrChannel?.enabled ? 1 : 0) +
		(indicators.hma?.enabled ? 1 : 0) +
		(indicators.adx?.enabled ? 1 : 0) +
		(indicators.ichimoku?.enabled ? 1 : 0) +
		(indicators.parabolicSar?.enabled ? 1 : 0) +
		(indicators.keltner?.enabled ? 1 : 0) +
		(indicators.volumeProfile?.enabled ? 1 : 0) +
		(indicators.supportResistance?.enabled ? 1 : 0);

	return (
		<div className="flex items-center gap-2">
			<Popover>
				<PopoverTrigger asChild>
					<Button variant="outline" size="sm" className="gap-2 h-8">
						<LineChart className="h-4 w-4" />
						Indicators
						{activeIndicatorsCount > 0 && (
							<Badge variant="secondary" className="ml-1 px-1.5 py-0 text-xs">
								{activeIndicatorsCount}
							</Badge>
						)}
					</Button>
				</PopoverTrigger>
				<PopoverContent className="w-80" align="start">
					<div className="space-y-4">
						<h4 className="font-medium text-sm">Technical Indicators</h4>
						<Separator />

						{/* SMA */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-blue-500" />
									<Label className="font-medium">SMA</Label>
									<span className="text-xs text-muted-foreground">Simple Moving Average</span>
								</div>
								<Switch
									checked={indicators.sma.enabled}
									onCheckedChange={(checked) => updateIndicator("sma", "enabled", checked)}
								/>
							</div>
							{indicators.sma.enabled && (
								<div className="flex items-center gap-2 pl-5">
									<span className="text-xs text-muted-foreground">Period:</span>
									<Select
										value={indicators.sma.period.toString()}
										onValueChange={(value) => updateIndicator("sma", "period", parseInt(value, 10))}
									>
										<SelectTrigger className="w-20 h-7">
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											{PERIOD_OPTIONS.map((period) => (
												<SelectItem key={period} value={period.toString()}>
													{period}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</div>
							)}
						</div>

						<Separator />

						{/* EMA */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-amber-500" />
									<Label className="font-medium">EMA</Label>
									<span className="text-xs text-muted-foreground">Exponential Moving Average</span>
								</div>
								<Switch
									checked={indicators.ema.enabled}
									onCheckedChange={(checked) => updateIndicator("ema", "enabled", checked)}
								/>
							</div>
							{indicators.ema.enabled && (
								<div className="flex items-center gap-2 pl-5">
									<span className="text-xs text-muted-foreground">Period:</span>
									<Select
										value={indicators.ema.period.toString()}
										onValueChange={(value) => updateIndicator("ema", "period", parseInt(value, 10))}
									>
										<SelectTrigger className="w-20 h-7">
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											{PERIOD_OPTIONS.map((period) => (
												<SelectItem key={period} value={period.toString()}>
													{period}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</div>
							)}
						</div>

						<Separator />

						{/* RSI */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-purple-500" />
									<Label className="font-medium">RSI</Label>
									<span className="text-xs text-muted-foreground">Relative Strength Index</span>
								</div>
								<Switch
									checked={indicators.rsi.enabled}
									onCheckedChange={(checked) => updateIndicator("rsi", "enabled", checked)}
								/>
							</div>
							{indicators.rsi.enabled && (
								<div className="flex items-center gap-2 pl-5">
									<span className="text-xs text-muted-foreground">Period:</span>
									<Select
										value={indicators.rsi.period.toString()}
										onValueChange={(value) => updateIndicator("rsi", "period", parseInt(value, 10))}
									>
										<SelectTrigger className="w-20 h-7">
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											{[7, 14, 21, 28].map((period) => (
												<SelectItem key={period} value={period.toString()}>
													{period}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</div>
							)}
						</div>

						<Separator />

						{/* MACD */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-cyan-500" />
									<Label className="font-medium">MACD</Label>
									<span className="text-xs text-muted-foreground">
										Moving Avg Convergence Divergence
									</span>
								</div>
								<Switch
									checked={indicators.macd?.enabled || false}
									onCheckedChange={(checked) => updateIndicator("macd", "enabled", checked)}
								/>
							</div>
						</div>

						<Separator />

						{/* Bollinger Bands */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-rose-500" />
									<Label className="font-medium">BB</Label>
									<span className="text-xs text-muted-foreground">Bollinger Bands</span>
								</div>
								<Switch
									checked={indicators.bollinger?.enabled || false}
									onCheckedChange={(checked) => updateIndicator("bollinger", "enabled", checked)}
								/>
							</div>
							{indicators.bollinger?.enabled && (
								<div className="flex items-center gap-4 pl-5">
									<div className="flex items-center gap-2">
										<span className="text-xs text-muted-foreground">Period:</span>
										<Select
											value={(indicators.bollinger.period || 20).toString()}
											onValueChange={(value) =>
												updateIndicator("bollinger", "period", parseInt(value, 10))
											}
										>
											<SelectTrigger className="w-16 h-7">
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												{[10, 20, 30, 50].map((period) => (
													<SelectItem key={period} value={period.toString()}>
														{period}
													</SelectItem>
												))}
											</SelectContent>
										</Select>
									</div>
									<div className="flex items-center gap-2">
										<span className="text-xs text-muted-foreground">StdDev:</span>
										<Select
											value={(indicators.bollinger.stdDev || 2).toString()}
											onValueChange={(value) =>
												updateIndicator("bollinger", "stdDev", parseFloat(value))
											}
										>
											<SelectTrigger className="w-16 h-7">
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												{[1, 1.5, 2, 2.5, 3].map((std) => (
													<SelectItem key={std} value={std.toString()}>
														{std}
													</SelectItem>
												))}
											</SelectContent>
										</Select>
									</div>
								</div>
							)}
						</div>

						<Separator />

						{/* VWAP */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-emerald-500" />
									<Label className="font-medium">VWAP</Label>
									<span className="text-xs text-muted-foreground">Volume Weighted Avg Price</span>
								</div>
								<Switch
									checked={indicators.vwap?.enabled || false}
									onCheckedChange={(checked) => updateIndicator("vwap", "enabled", checked)}
								/>
							</div>
						</div>

						<Separator />

						{/* ATR */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-orange-500" />
									<Label className="font-medium">ATR</Label>
									<span className="text-xs text-muted-foreground">Average True Range</span>
								</div>
								<Switch
									checked={indicators.atr?.enabled || false}
									onCheckedChange={(checked) => updateIndicator("atr", "enabled", checked)}
								/>
							</div>
							{indicators.atr?.enabled && (
								<div className="flex items-center gap-2 pl-5">
									<span className="text-xs text-muted-foreground">Period:</span>
									<Select
										value={(indicators.atr.period || 14).toString()}
										onValueChange={(value) => updateIndicator("atr", "period", parseInt(value, 10))}
									>
										<SelectTrigger className="w-20 h-7">
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											{[7, 14, 21, 28, 50].map((period) => (
												<SelectItem key={period} value={period.toString()}>
													{period}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</div>
							)}
						</div>

						<Separator />

						{/* VWMA */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-lime-500" />
									<Label className="font-medium">VWMA</Label>
									<span className="text-xs text-muted-foreground">Volume Weighted MA</span>
								</div>
								<Switch
									checked={indicators.vwma?.enabled || false}
									onCheckedChange={(checked) => updateIndicator("vwma", "enabled", checked)}
								/>
							</div>
							{indicators.vwma?.enabled && (
								<div className="flex items-center gap-2 pl-5">
									<span className="text-xs text-muted-foreground">Period:</span>
									<Select
										value={(indicators.vwma.period || 20).toString()}
										onValueChange={(value) =>
											updateIndicator("vwma", "period", parseInt(value, 10))
										}
									>
										<SelectTrigger className="w-20 h-7">
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											{[10, 20, 30, 50, 100, 200].map((period) => (
												<SelectItem key={period} value={period.toString()}>
													{period}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</div>
							)}
						</div>

						<Separator />

						{/* SMA +/- ATR Channel */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-sky-500" />
									<Label className="font-medium">SMA +/- ATR</Label>
									<span className="text-xs text-muted-foreground">SMA channel by ATR</span>
								</div>
								<Switch
									checked={indicators.atrChannel?.enabled || false}
									onCheckedChange={(checked) => updateIndicator("atrChannel", "enabled", checked)}
								/>
							</div>
							{indicators.atrChannel?.enabled && (
								<div className="grid grid-cols-3 gap-2 pl-5">
									<Select
										value={(indicators.atrChannel.smaPeriod || 50).toString()}
										onValueChange={(value) =>
											updateIndicator("atrChannel", "smaPeriod", parseInt(value, 10))
										}
									>
										<SelectTrigger className="h-7">
											<SelectValue placeholder="SMA" />
										</SelectTrigger>
										<SelectContent>
											{[20, 50, 100, 200].map((period) => (
												<SelectItem key={`ac-s-${period}`} value={period.toString()}>
													SMA {period}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
									<Select
										value={(indicators.atrChannel.atrPeriod || 14).toString()}
										onValueChange={(value) =>
											updateIndicator("atrChannel", "atrPeriod", parseInt(value, 10))
										}
									>
										<SelectTrigger className="h-7">
											<SelectValue placeholder="ATR" />
										</SelectTrigger>
										<SelectContent>
											{[7, 14, 21, 28, 50].map((period) => (
												<SelectItem key={`ac-a-${period}`} value={period.toString()}>
													ATR {period}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
									<Select
										value={(indicators.atrChannel.multiplier || 1.5).toString()}
										onValueChange={(value) =>
											updateIndicator("atrChannel", "multiplier", parseFloat(value))
										}
									>
										<SelectTrigger className="h-7">
											<SelectValue placeholder="x" />
										</SelectTrigger>
										<SelectContent>
											{[1, 1.5, 2, 2.5, 3].map((mult) => (
												<SelectItem key={`ac-m-${mult}`} value={mult.toString()}>
													x{mult}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</div>
							)}
						</div>

						<Separator />

						{/* HMA */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-teal-500" />
									<Label className="font-medium">HMA</Label>
									<span className="text-xs text-muted-foreground">Hull Moving Average</span>
								</div>
								<Switch
									checked={indicators.hma?.enabled || false}
									onCheckedChange={(checked) => updateIndicator("hma", "enabled", checked)}
								/>
							</div>
							{indicators.hma?.enabled && (
								<div className="flex items-center gap-2 pl-5">
									<span className="text-xs text-muted-foreground">Period:</span>
									<Select
										value={(indicators.hma.period || 20).toString()}
										onValueChange={(value) => updateIndicator("hma", "period", parseInt(value, 10))}
									>
										<SelectTrigger className="w-20 h-7">
											<SelectValue />
										</SelectTrigger>
										<SelectContent>
											{[9, 16, 20, 34, 55].map((period) => (
												<SelectItem key={`hma-${period}`} value={period.toString()}>
													{period}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</div>
							)}
						</div>

						<Separator />

						{/* Ichimoku */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-indigo-500" />
									<Label className="font-medium">Ichimoku</Label>
									<span className="text-xs text-muted-foreground">Cloud baseline overlay</span>
								</div>
								<Switch
									checked={indicators.ichimoku?.enabled || false}
									onCheckedChange={(checked) => updateIndicator("ichimoku", "enabled", checked)}
								/>
							</div>
						</div>

						<Separator />

						{/* Parabolic SAR */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-pink-500" />
									<Label className="font-medium">Parabolic SAR</Label>
									<span className="text-xs text-muted-foreground">Trend stop/reversal markers</span>
								</div>
								<Switch
									checked={indicators.parabolicSar?.enabled || false}
									onCheckedChange={(checked) => updateIndicator("parabolicSar", "enabled", checked)}
								/>
							</div>
						</div>

						<Separator />

						{/* Keltner */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-fuchsia-500" />
									<Label className="font-medium">Keltner</Label>
									<span className="text-xs text-muted-foreground">EMA channel by ATR</span>
								</div>
								<Switch
									checked={indicators.keltner?.enabled || false}
									onCheckedChange={(checked) => updateIndicator("keltner", "enabled", checked)}
								/>
							</div>
						</div>

						<Separator />

						{/* ADX */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-violet-500" />
									<Label className="font-medium">ADX</Label>
									<span className="text-xs text-muted-foreground">Trend strength</span>
								</div>
								<Switch
									checked={indicators.adx?.enabled || false}
									onCheckedChange={(checked) => updateIndicator("adx", "enabled", checked)}
								/>
							</div>
						</div>

						<Separator />

						{/* Volume Profile */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-emerald-400" />
									<Label className="font-medium">Volume Profile</Label>
									<span className="text-xs text-muted-foreground">High-volume price levels</span>
								</div>
								<Switch
									checked={indicators.volumeProfile?.enabled || false}
									onCheckedChange={(checked) =>
										updateIndicator("volumeProfile", "enabled", checked)
									}
								/>
							</div>
						</div>

						<Separator />

						{/* Support / Resistance */}
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<div className="w-3 h-3 rounded-full bg-red-400" />
									<Label className="font-medium">S/R Levels</Label>
									<span className="text-xs text-muted-foreground">
										Support and resistance bands
									</span>
								</div>
								<Switch
									checked={indicators.supportResistance?.enabled || false}
									onCheckedChange={(checked) =>
										updateIndicator("supportResistance", "enabled", checked)
									}
								/>
							</div>
						</div>
					</div>
				</PopoverContent>
			</Popover>

			{/* Active Indicators Badges */}
			<div className="flex items-center gap-1">
				{indicators.sma.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-blue-500/50 text-blue-500">
						<div className="w-2 h-2 rounded-full bg-blue-500" />
						SMA {indicators.sma.period}
					</Badge>
				)}
				{indicators.ema.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-amber-500/50 text-amber-500">
						<div className="w-2 h-2 rounded-full bg-amber-500" />
						EMA {indicators.ema.period}
					</Badge>
				)}
				{indicators.rsi.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-purple-500/50 text-purple-500">
						<div className="w-2 h-2 rounded-full bg-purple-500" />
						RSI {indicators.rsi.period}
					</Badge>
				)}
				{indicators.macd?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-cyan-500/50 text-cyan-500">
						<div className="w-2 h-2 rounded-full bg-cyan-500" />
						MACD
					</Badge>
				)}
				{indicators.bollinger?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-rose-500/50 text-rose-500">
						<div className="w-2 h-2 rounded-full bg-rose-500" />
						BB
					</Badge>
				)}
				{indicators.vwap?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-emerald-500/50 text-emerald-500">
						<div className="w-2 h-2 rounded-full bg-emerald-500" />
						VWAP
					</Badge>
				)}
				{indicators.atr?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-orange-500/50 text-orange-500">
						<div className="w-2 h-2 rounded-full bg-orange-500" />
						ATR {indicators.atr.period}
					</Badge>
				)}
				{indicators.vwma?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-lime-500/50 text-lime-500">
						<div className="w-2 h-2 rounded-full bg-lime-500" />
						VWMA {indicators.vwma.period}
					</Badge>
				)}
				{indicators.atrChannel?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-sky-500/50 text-sky-500">
						<div className="w-2 h-2 rounded-full bg-sky-500" />
						SMA +/- ATR
					</Badge>
				)}
				{indicators.hma?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-teal-500/50 text-teal-500">
						<div className="w-2 h-2 rounded-full bg-teal-500" />
						HMA {indicators.hma.period}
					</Badge>
				)}
				{indicators.ichimoku?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-indigo-500/50 text-indigo-500">
						<div className="w-2 h-2 rounded-full bg-indigo-500" />
						Ichimoku
					</Badge>
				)}
				{indicators.parabolicSar?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-pink-500/50 text-pink-500">
						<div className="w-2 h-2 rounded-full bg-pink-500" />
						Parabolic SAR
					</Badge>
				)}
				{indicators.keltner?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-fuchsia-500/50 text-fuchsia-500">
						<div className="w-2 h-2 rounded-full bg-fuchsia-500" />
						Keltner
					</Badge>
				)}
				{indicators.adx?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-violet-500/50 text-violet-500">
						<div className="w-2 h-2 rounded-full bg-violet-500" />
						ADX
					</Badge>
				)}
				{indicators.volumeProfile?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-emerald-400/50 text-emerald-400">
						<div className="w-2 h-2 rounded-full bg-emerald-400" />
						Vol Profile
					</Badge>
				)}
				{indicators.supportResistance?.enabled && (
					<Badge variant="outline" className="gap-1 text-xs border-red-400/50 text-red-400">
						<div className="w-2 h-2 rounded-full bg-red-400" />
						S/R
					</Badge>
				)}
			</div>
		</div>
	);
}
