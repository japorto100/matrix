"use client";

// Returns the current user's role from the NextAuth session.
// Falls back to "viewer" (most restrictive) when session is loading or absent.

import { useSession } from "next-auth/react";

export function useControlRole(): string {
	const { data: session } = useSession();
	return (session?.user as { role?: string } | undefined)?.role ?? "viewer";
}
