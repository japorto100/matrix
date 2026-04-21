"use client";

// ControlMode hook — URL param ?mode=dev + localStorage sync (D20)
// Single source of truth: URL. localStorage only used as initial fallback on page load.

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { ControlMode } from "./types";

const STORAGE_KEY = "matrix:control-mode";

function readStored(): ControlMode {
	if (typeof window === "undefined") return "user";
	const v = window.localStorage.getItem(STORAGE_KEY);
	return v === "dev" ? "dev" : "user";
}

function writeStored(mode: ControlMode): void {
	if (typeof window === "undefined") return;
	window.localStorage.setItem(STORAGE_KEY, mode);
}

/**
 * useControlMode — get/set the User vs Developer Mode.
 *
 * Precedence:
 * 1. If `?mode=dev` is in the URL → dev
 * 2. If `?mode=user` is in the URL → user
 * 3. Fallback to localStorage (or "user" on first ever load)
 *
 * Setting the mode updates both URL (via pushState) and localStorage.
 */
export function useControlMode(): {
	mode: ControlMode;
	setMode: (mode: ControlMode) => void;
	isDev: boolean;
} {
	const searchParams = useSearchParams();
	const [mode, setModeState] = useState<ControlMode>("user");

	// On mount: read URL param OR localStorage
	useEffect(() => {
		const urlMode = searchParams.get("mode");
		if (urlMode === "dev" || urlMode === "user") {
			setModeState(urlMode);
			writeStored(urlMode);
		} else {
			setModeState(readStored());
		}
	}, [searchParams]);

	const setMode = useCallback((next: ControlMode) => {
		setModeState(next);
		writeStored(next);
		// Update URL in place (no full navigation) so ?mode=... is shareable
		if (typeof window !== "undefined") {
			const url = new URL(window.location.href);
			url.searchParams.set("mode", next);
			window.history.replaceState(null, "", url.toString());
		}
	}, []);

	return { mode, setMode, isDev: mode === "dev" };
}
