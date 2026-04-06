"use client";

import { Check, Moon, Palette, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function ThemePicker() {
	const { resolvedTheme, setTheme } = useTheme();

	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>
				<Button variant="ghost" size="icon" className="h-7 w-7">
					{resolvedTheme === "light" ? (
						<Sun className="h-3.5 w-3.5" />
					) : resolvedTheme === "dark" ? (
						<Moon className="h-3.5 w-3.5" />
					) : (
						<Palette className="h-3.5 w-3.5" />
					)}
				</Button>
			</DropdownMenuTrigger>
			<DropdownMenuContent align="end">
				<DropdownMenuItem onClick={() => setTheme("light")}>
					<Sun className="mr-2 h-4 w-4" />
					Light
					{resolvedTheme === "light" && <Check className="ml-auto h-3 w-3" />}
				</DropdownMenuItem>
				<DropdownMenuItem onClick={() => setTheme("dark")}>
					<Moon className="mr-2 h-4 w-4" />
					Dark
					{resolvedTheme === "dark" && <Check className="ml-auto h-3 w-3" />}
				</DropdownMenuItem>
				<DropdownMenuItem onClick={() => setTheme("blue-dark")}>
					<Palette className="mr-2 h-4 w-4 text-blue-400" />
					Blue Dark
					{resolvedTheme === "blue-dark" && <Check className="ml-auto h-3 w-3" />}
				</DropdownMenuItem>
				<DropdownMenuItem onClick={() => setTheme("green-dark")}>
					<Palette className="mr-2 h-4 w-4 text-emerald-400" />
					Green Dark
					{resolvedTheme === "green-dark" && <Check className="ml-auto h-3 w-3" />}
				</DropdownMenuItem>
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
