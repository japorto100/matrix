import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useCurrentRoute } from "../useCurrentRoute";

vi.mock("next/navigation", () => ({
	usePathname: vi.fn(),
}));

import { usePathname } from "next/navigation";

describe("useCurrentRoute", () => {
	it("parses root", () => {
		(usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/");
		expect(renderHook(() => useCurrentRoute()).result.current).toEqual({
			pathname: "/",
			segment: "home",
			subtab: null,
		});
	});

	it("parses /control/agents", () => {
		(usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/control/agents");
		expect(renderHook(() => useCurrentRoute()).result.current).toEqual({
			pathname: "/control/agents",
			segment: "control",
			subtab: "agents",
		});
	});

	it("parses /memory/timeline", () => {
		(usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/memory/timeline");
		expect(renderHook(() => useCurrentRoute()).result.current).toEqual({
			pathname: "/memory/timeline",
			segment: "memory",
			subtab: "timeline",
		});
	});

	it("parses /files with no subtab", () => {
		(usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/files");
		expect(renderHook(() => useCurrentRoute()).result.current).toEqual({
			pathname: "/files",
			segment: "files",
			subtab: null,
		});
	});

	it("returns unknown segment for /random/path", () => {
		(usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/random/path");
		expect(renderHook(() => useCurrentRoute()).result.current).toEqual({
			pathname: "/random/path",
			segment: "unknown",
			subtab: "path",
		});
	});
});
