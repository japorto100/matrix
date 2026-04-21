"use client";

import { Activity, DollarSign, TrendingUp } from "lucide-react";
import { useMemo } from "react";
import {
	Bar,
	BarChart,
	CartesianGrid,
	Cell,
	Pie,
	PieChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSpendActivity, useSpendByModel, useSpendByProvider } from "@/lib/queries/hooks";

const COLORS = [
	"hsl(var(--primary))",
	"hsl(210 80% 55%)",
	"hsl(150 60% 45%)",
	"hsl(35 90% 55%)",
	"hsl(280 60% 55%)",
	"hsl(0 70% 55%)",
];

function formatDate(dateStr: string): string {
	const d = new Date(dateStr);
	return `${d.getMonth() + 1}/${d.getDate()}`;
}

function formatTokens(n: number): string {
	if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
	if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
	return String(n);
}

export function SpendDashboard() {
	const activityQuery = useSpendActivity();
	const modelQuery = useSpendByModel();
	const providerQuery = useSpendByProvider();

	const activity = activityQuery.data;
	const modelData = modelQuery.data;
	const providerData = providerQuery.data;

	const hasData = activity?.daily_data?.length || modelData?.data?.length || providerData?.length;
	const isLoading = activityQuery.isLoading || modelQuery.isLoading;

	const dailyChartData = useMemo(() => {
		return (activity?.daily_data ?? []).map((d) => ({
			date: formatDate(d.date),
			requests: d.api_requests,
			tokens: d.total_tokens,
		}));
	}, [activity]);

	const providerPieData = useMemo(() => {
		if (!providerData || !Array.isArray(providerData)) return [];
		return providerData
			.filter((p) => p.spend > 0)
			.sort((a, b) => b.spend - a.spend)
			.slice(0, 6);
	}, [providerData]);

	if (isLoading) {
		return (
			<div className="text-muted-foreground text-center py-8 text-sm">Loading spend data...</div>
		);
	}

	if (!hasData) {
		return (
			<div className="text-muted-foreground text-center py-8 text-sm border border-dashed border-border rounded-lg">
				<DollarSign className="h-6 w-6 mx-auto mb-2 opacity-40" />
				<p>No spend data yet. Send some messages to start tracking.</p>
				<p className="text-[10px] mt-1">Requires LITELLM_DATABASE_URL to be configured.</p>
			</div>
		);
	}

	return (
		<div className="space-y-4">
			{/* Summary cards */}
			<div className="grid grid-cols-3 gap-3">
				<Card>
					<CardContent className="pt-4 pb-3 px-4">
						<div className="flex items-center gap-2 text-xs text-muted-foreground">
							<Activity className="h-3.5 w-3.5" />
							<span>Requests (30d)</span>
						</div>
						<div className="text-lg font-semibold mt-1">
							{(activity?.sum_api_requests ?? 0).toLocaleString()}
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="pt-4 pb-3 px-4">
						<div className="flex items-center gap-2 text-xs text-muted-foreground">
							<TrendingUp className="h-3.5 w-3.5" />
							<span>Tokens (30d)</span>
						</div>
						<div className="text-lg font-semibold mt-1">
							{formatTokens(activity?.sum_total_tokens ?? 0)}
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="pt-4 pb-3 px-4">
						<div className="flex items-center gap-2 text-xs text-muted-foreground">
							<DollarSign className="h-3.5 w-3.5" />
							<span>Providers</span>
						</div>
						<div className="text-lg font-semibold mt-1">
							{Array.isArray(providerData) ? providerData.length : 0}
						</div>
					</CardContent>
				</Card>
			</div>

			{/* Daily activity bar chart */}
			{dailyChartData.length > 0 && (
				<Card>
					<CardHeader className="pb-2">
						<CardTitle className="text-sm font-medium">Daily Requests</CardTitle>
					</CardHeader>
					<CardContent className="pt-0">
						<ResponsiveContainer width="100%" height={180}>
							<BarChart data={dailyChartData} margin={{ left: -20, right: 0 }}>
								<CartesianGrid strokeDasharray="3 3" className="stroke-border" />
								<XAxis dataKey="date" tick={{ fontSize: 10 }} className="fill-muted-foreground" />
								<YAxis tick={{ fontSize: 10 }} className="fill-muted-foreground" />
								<Tooltip
									contentStyle={{
										fontSize: 11,
										background: "hsl(var(--popover))",
										border: "1px solid hsl(var(--border))",
										borderRadius: 6,
									}}
								/>
								<Bar dataKey="requests" fill="hsl(var(--primary))" radius={[2, 2, 0, 0]} />
							</BarChart>
						</ResponsiveContainer>
					</CardContent>
				</Card>
			)}

			<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
				{/* Spend by provider pie */}
				{providerPieData.length > 0 && (
					<Card>
						<CardHeader className="pb-2">
							<CardTitle className="text-sm font-medium">Spend by Provider</CardTitle>
						</CardHeader>
						<CardContent className="pt-0 flex items-center gap-4">
							<ResponsiveContainer width={120} height={120}>
								<PieChart>
									<Pie
										data={providerPieData}
										dataKey="spend"
										nameKey="provider"
										cx="50%"
										cy="50%"
										innerRadius={30}
										outerRadius={55}
									>
										{providerPieData.map((_entry, i) => (
											<Cell key={_entry.provider} fill={COLORS[i % COLORS.length]} />
										))}
									</Pie>
								</PieChart>
							</ResponsiveContainer>
							<div className="space-y-1">
								{providerPieData.map((p, i) => (
									<div key={p.provider} className="flex items-center gap-2 text-xs">
										<div
											className="h-2.5 w-2.5 rounded-full shrink-0"
											style={{ backgroundColor: COLORS[i % COLORS.length] }}
										/>
										<span className="text-muted-foreground">{p.provider}</span>
										<span className="font-mono font-medium ml-auto">${p.spend.toFixed(2)}</span>
									</div>
								))}
							</div>
						</CardContent>
					</Card>
				)}

				{/* Top models table */}
				{modelData?.data && modelData.data.length > 0 && (
					<Card>
						<CardHeader className="pb-2">
							<CardTitle className="text-sm font-medium">Top Models</CardTitle>
						</CardHeader>
						<CardContent className="pt-0">
							<div className="space-y-1.5">
								{modelData.data.slice(0, 8).map((m) => (
									<div key={m.model_group} className="flex items-center justify-between text-xs">
										<span className="text-muted-foreground truncate max-w-[60%] font-mono">
											{m.model_group}
										</span>
										<div className="flex items-center gap-2">
											<Badge variant="secondary" className="text-[9px] h-4 px-1.5">
												{m.api_requests} req
											</Badge>
											<span className="font-mono text-[10px]">{formatTokens(m.total_tokens)}</span>
										</div>
									</div>
								))}
							</div>
						</CardContent>
					</Card>
				)}
			</div>
		</div>
	);
}
