"use client";

import { usePathname } from "next/navigation";
import { useMemo } from "react";

export interface CurrentRoute {
	pathname: string;
	segment: "home" | "matrix" | "files" | "memory" | "control" | "unknown";
	subtab: string | null;
}

const KNOWN_SEGMENTS = ["matrix", "files", "memory", "control"] as const;

export function useCurrentRoute(): CurrentRoute {
	const pathname = usePathname();
	return useMemo(() => {
		if (!pathname || pathname === "/") {
			return { pathname: pathname ?? "/", segment: "home", subtab: null };
		}
		const parts = pathname.split("/").filter(Boolean);
		const first = parts[0] ?? "";
		const segment = (KNOWN_SEGMENTS as readonly string[]).includes(first)
			? (first as CurrentRoute["segment"])
			: "unknown";
		return { pathname, segment, subtab: parts[1] ?? null };
	}, [pathname]);
}
