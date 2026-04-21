"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

/**
 * Theme + Font-Size. Theme via next-themes (schon in webapp providers).
 * Font-Size persistiert in localStorage — CSS-Root-var `--font-size-scale`
 * kann in globals.css genutzt werden.
 */
export function AppearanceTab() {
	const { theme, setTheme } = useTheme();
	const [mounted, setMounted] = useState(false);
	const [fontScale, setFontScale] = useState<"small" | "medium" | "large">(() => {
		if (typeof window === "undefined") return "medium";
		return (localStorage.getItem("matrix.fontScale") as "small" | "medium" | "large") ?? "medium";
	});

	useEffect(() => setMounted(true), []);

	useEffect(() => {
		if (typeof document === "undefined") return;
		const scale = fontScale === "small" ? "0.9" : fontScale === "large" ? "1.1" : "1";
		document.documentElement.style.setProperty("--matrix-font-scale", scale);
		localStorage.setItem("matrix.fontScale", fontScale);
	}, [fontScale]);

	if (!mounted) return null;

	const themes = [
		{ value: "light", label: "Hell", icon: Sun },
		{ value: "dark", label: "Dunkel", icon: Moon },
		{ value: "system", label: "System", icon: Monitor },
	];

	return (
		<div className="space-y-5">
			<div>
				<h3 className="text-sm font-semibold mb-2">Theme</h3>
				<div className="grid grid-cols-3 gap-2">
					{themes.map((t) => {
						const Icon = t.icon;
						const isActive = theme === t.value;
						return (
							<Button
								key={t.value}
								variant={isActive ? "default" : "outline"}
								onClick={() => setTheme(t.value)}
								className="flex flex-col h-auto py-3 gap-1"
							>
								<Icon className="h-4 w-4" />
								<span className="text-xs">{t.label}</span>
							</Button>
						);
					})}
				</div>
			</div>

			<div>
				<h3 className="text-sm font-semibold mb-2">Schriftgroesse</h3>
				<div className="grid grid-cols-3 gap-2">
					{(["small", "medium", "large"] as const).map((size) => {
						const isActive = fontScale === size;
						const label = size === "small" ? "Klein" : size === "large" ? "Gross" : "Mittel";
						return (
							<Button
								key={size}
								variant={isActive ? "default" : "outline"}
								onClick={() => setFontScale(size)}
								className="h-8 text-xs"
							>
								{label}
							</Button>
						);
					})}
				</div>
				<p className="text-[10px] text-muted-foreground mt-2">
					Aenderung beeinflusst die CSS-Variable <code>--matrix-font-scale</code>.
				</p>
			</div>
		</div>
	);
}
