"use client";

import { Activity, BarChart3, DollarSign, Search, Star, TrendingUp, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { FusionSymbol } from "@/lib/fusion-symbols";

interface SymbolSearchProps {
	query: string;
	open: boolean;
	results: FusionSymbol[];
	favorites: string[];
	popularSymbols: FusionSymbol[];
	onQueryChange: (value: string) => void;
	onOpenChange: (value: boolean) => void;
	onSelect: (symbol: FusionSymbol) => void;
	onToggleFavorite: (symbol: string) => void;
	searchPending?: boolean;
}

function getSymbolIcon(type: FusionSymbol["type"]) {
	switch (type) {
		case "crypto":
			return <Activity className="h-4 w-4 text-orange-400" />;
		case "fx":
			return <DollarSign className="h-4 w-4 text-green-400" />;
		case "index":
			return <BarChart3 className="h-4 w-4 text-violet-400" />;
		default:
			return <TrendingUp className="h-4 w-4 text-blue-400" />;
	}
}

export function SymbolSearch({
	query,
	open,
	results,
	favorites,
	popularSymbols,
	onQueryChange,
	onOpenChange,
	onSelect,
	onToggleFavorite,
	searchPending = false,
}: SymbolSearchProps) {
	const containerRef = useRef<HTMLDivElement>(null);
	const [highlightedIndex, setHighlightedIndex] = useState(-1);

	useEffect(() => {
		const handler = (event: MouseEvent) => {
			if (!containerRef.current?.contains(event.target as Node)) {
				onOpenChange(false);
			}
		};
		document.addEventListener("mousedown", handler);
		return () => document.removeEventListener("mousedown", handler);
	}, [onOpenChange]);

	const showPopular = query.trim().length === 0;
	const selectableSymbols = useMemo(
		() => (showPopular ? popularSymbols : results),
		[popularSymbols, results, showPopular],
	);
	const showEmpty = !showPopular && results.length === 0;

	useEffect(() => {
		if (!open) {
			setHighlightedIndex(-1);
			return;
		}
		setHighlightedIndex(selectableSymbols.length > 0 ? 0 : -1);
	}, [open, selectableSymbols.length]);

	useEffect(() => {
		if (highlightedIndex < selectableSymbols.length) return;
		setHighlightedIndex(selectableSymbols.length > 0 ? selectableSymbols.length - 1 : -1);
	}, [highlightedIndex, selectableSymbols.length]);

	return (
		<div ref={containerRef} className="relative">
			<div className="flex items-center gap-1 bg-background/50 border border-border rounded-lg px-2">
				<Search className="h-4 w-4 text-muted-foreground" />
				<Input
					id="fusion-symbol-search"
					name="fusionSymbolSearch"
					type="text"
					placeholder="Search symbol..."
					value={query}
					onChange={(e) => {
						onQueryChange(e.target.value);
						onOpenChange(true);
					}}
					onFocus={() => onOpenChange(true)}
					onKeyDown={(event) => {
						if (!open && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
							onOpenChange(true);
							return;
						}

						if (event.key === "Escape") {
							onOpenChange(false);
							return;
						}

						if (event.key === "ArrowDown") {
							event.preventDefault();
							if (selectableSymbols.length === 0) return;
							setHighlightedIndex((prev) => (prev < selectableSymbols.length - 1 ? prev + 1 : 0));
							return;
						}

						if (event.key === "ArrowUp") {
							event.preventDefault();
							if (selectableSymbols.length === 0) return;
							setHighlightedIndex((prev) => (prev <= 0 ? selectableSymbols.length - 1 : prev - 1));
							return;
						}

						if (event.key === "Enter") {
							const selected =
								highlightedIndex >= 0 ? selectableSymbols[highlightedIndex] : selectableSymbols[0];
							if (selected) {
								event.preventDefault();
								onSelect(selected);
							}
						}
					}}
					className="border-none bg-transparent px-0 shadow-none focus-visible:ring-0"
				/>
				{query ? (
					<button
						type="button"
						className="text-muted-foreground hover:text-foreground"
						onClick={() => {
							onQueryChange("");
							onOpenChange(true);
						}}
					>
						<X className="h-4 w-4" />
					</button>
				) : null}
			</div>

			{open ? (
				<div className="absolute top-full left-0 mt-1 w-80 bg-card border border-border rounded-lg shadow-lg z-50">
					{showPopular ? (
						<div className="p-3 border-b border-border">
							<p className="text-xs text-muted-foreground mb-2">Popular</p>
							<div className="flex flex-wrap gap-2">
								{popularSymbols.map((symbol, index) => (
									<button
										key={symbol.symbol}
										type="button"
										onClick={() => onSelect(symbol)}
										className={`px-2.5 py-1 rounded-md text-xs ${highlightedIndex === index ? "bg-accent" : "bg-accent/40 hover:bg-accent"}`}
									>
										{symbol.symbol}
									</button>
								))}
							</div>
						</div>
					) : null}

					<ScrollArea className="max-h-72">
						{showEmpty ? (
							<div className="px-3 py-4 text-sm text-muted-foreground">No results</div>
						) : searchPending ? (
							<div className="px-3 py-4 text-sm text-muted-foreground">Searching...</div>
						) : (
							results.map((symbol, index) => {
								const isFavorite = favorites.includes(symbol.symbol);
								return (
									<div
										key={symbol.symbol}
										role="button"
										tabIndex={0}
										onClick={() => onSelect(symbol)}
										onMouseEnter={() => setHighlightedIndex(index)}
										onKeyDown={(event) => {
											if (event.key === "Enter" || event.key === " ") {
												event.preventDefault();
												onSelect(symbol);
											}
										}}
										className={`w-full px-3 py-2.5 flex items-center justify-between ${
											highlightedIndex === index ? "bg-accent/60" : "hover:bg-accent/50"
										}`}
									>
										<div className="flex items-center gap-2.5 text-left">
											<div className="h-8 w-8 rounded-md bg-accent/40 flex items-center justify-center">
												{getSymbolIcon(symbol.type)}
											</div>
											<div>
												<div className="text-sm font-medium">{symbol.symbol}</div>
												<div className="text-xs text-muted-foreground">{symbol.name}</div>
											</div>
										</div>
										<div className="flex items-center gap-2">
											<Badge variant="outline" className="text-[10px]">
												{symbol.type.toUpperCase()}
											</Badge>
											<button
												type="button"
												className={`p-1 rounded ${isFavorite ? "text-amber-500" : "text-muted-foreground hover:text-amber-500"}`}
												onClick={(e) => {
													e.stopPropagation();
													onToggleFavorite(symbol.symbol);
												}}
												aria-label={`Toggle favorite ${symbol.symbol}`}
											>
												<Star className={`h-4 w-4 ${isFavorite ? "fill-amber-500" : ""}`} />
											</button>
										</div>
									</div>
								);
							})
						)}
					</ScrollArea>
				</div>
			) : null}
		</div>
	);
}
