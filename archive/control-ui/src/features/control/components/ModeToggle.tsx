"use client";

// ModeToggle — compact User / Dev mode switch for ControlTopNav
// Persists via useControlMode hook (URL param + localStorage)

import { Code2, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useControlMode } from "../mode";

export function ModeToggle() {
	const { mode, setMode } = useControlMode();

	return (
		<div
			className="flex items-center gap-0.5 rounded-md border border-border bg-card/40 p-0.5"
			role="group"
			aria-label="Control mode"
		>
			<Button
				variant="ghost"
				size="sm"
				onClick={() => setMode("user")}
				aria-pressed={mode === "user"}
				className={cn(
					"h-6 gap-1 px-2 text-[10px] font-medium transition-colors",
					mode === "user"
						? "bg-accent text-foreground hover:bg-accent"
						: "text-muted-foreground hover:text-foreground hover:bg-transparent",
				)}
			>
				<Eye className="h-2.5 w-2.5" />
				User
			</Button>
			<Button
				variant="ghost"
				size="sm"
				onClick={() => setMode("dev")}
				aria-pressed={mode === "dev"}
				className={cn(
					"h-6 gap-1 px-2 text-[10px] font-medium transition-colors",
					mode === "dev"
						? "bg-accent text-foreground hover:bg-accent"
						: "text-muted-foreground hover:text-foreground hover:bg-transparent",
				)}
			>
				<Code2 className="h-2.5 w-2.5" />
				Developer
			</Button>
		</div>
	);
}
