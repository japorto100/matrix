"use client";

// DW9 tab wrapper — data/spreadsheet tab (v1.5 — SheetJS + TanStack Table)

import { Construction, TableIcon } from "lucide-react";

export function FilesDataTab() {
	return (
		<div className="flex h-full min-h-0">
			<div className="w-56 shrink-0 flex flex-col gap-2 border-r border-border p-3 overflow-y-auto">
				<p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">
					Data Files
				</p>
				<p className="text-xs text-muted-foreground/60 italic">No data files yet.</p>
			</div>

			<div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center text-muted-foreground">
				<div className="relative">
					<TableIcon className="h-8 w-8 text-muted-foreground/30" />
					<Construction className="h-4 w-4 text-muted-foreground/40 absolute -bottom-1 -right-1" />
				</div>
				<p className="text-sm font-medium">Data viewer coming in v1.5</p>
				<p className="text-xs text-muted-foreground/50 font-mono">
					DW9 — SheetJS + TanStack Table (CSV / XLSX / JSON)
				</p>
			</div>
		</div>
	);
}
