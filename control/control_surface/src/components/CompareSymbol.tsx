"use client";

import { Check, Layers, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";

interface CompareSymbolProps {
	currentCompare?: string | null;
	onCompare: (symbol: string | null) => void;
}

const POPULAR_COMPARES = [
	{ symbol: "BTC/USD", name: "Bitcoin" },
	{ symbol: "ETH/USD", name: "Ethereum" },
	{ symbol: "SPX", name: "S&P 500" },
	{ symbol: "DJI", name: "Dow Jones" },
	{ symbol: "XAU/USD", name: "Gold" },
	{ symbol: "DXY", name: "Dollar Index" },
];

export function CompareSymbol({ currentCompare, onCompare }: CompareSymbolProps) {
	const [search, setSearch] = useState("");

	const filteredSymbols = POPULAR_COMPARES.filter(
		(s) =>
			s.symbol.toLowerCase().includes(search.toLowerCase()) ||
			s.name.toLowerCase().includes(search.toLowerCase()),
	);

	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>
				<Button variant={currentCompare ? "default" : "outline"} size="sm" className="gap-2">
					<Layers className="h-4 w-4" />
					<span className="hidden sm:inline">{currentCompare ? currentCompare : "Compare"}</span>
				</Button>
			</DropdownMenuTrigger>
			<DropdownMenuContent align="end" className="w-56">
				{currentCompare && (
					<>
						<DropdownMenuItem onClick={() => onCompare(null)}>
							<X className="h-4 w-4 mr-2" />
							Remove {currentCompare}
						</DropdownMenuItem>
						<DropdownMenuSeparator />
					</>
				)}

				<div className="p-2">
					<Input
						placeholder="Search symbol..."
						value={search}
						onChange={(e) => setSearch(e.target.value)}
						className="h-8"
					/>
				</div>

				<DropdownMenuSeparator />

				<div className="max-h-48 overflow-y-auto">
					{filteredSymbols.map((s) => (
						<DropdownMenuItem
							key={s.symbol}
							onClick={() => onCompare(s.symbol)}
							className={currentCompare === s.symbol ? "bg-accent" : ""}
						>
							<span className="flex-1">{s.symbol}</span>
							<span className="text-xs text-muted-foreground mr-2">{s.name}</span>
							{currentCompare === s.symbol && <Check className="h-4 w-4" />}
						</DropdownMenuItem>
					))}
				</div>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}

export default CompareSymbol;
