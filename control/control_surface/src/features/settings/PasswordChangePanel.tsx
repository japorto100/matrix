"use client";

/**
 * SOTA 2026 Password Change Panel
 * Next.js 16 / React 19 Implementation using useActionState
 */

import { AlertCircle, KeyRound, Loader2, ShieldCheck } from "lucide-react";
import { useActionState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { type ChangePasswordResult, changePassword } from "@/lib/actions/auth-actions";

const initialState: ChangePasswordResult = { success: false, error: "" };

export function PasswordChangePanel() {
	const { toast } = useToast();
	// React 19: useActionState for seamless server-action handling
	const [state, action, isPending] = useActionState(changePassword, initialState);

	useEffect(() => {
		if (state.success) {
			toast({
				title: "Security Updated",
				description: "Your account password has been successfully rotated.",
				variant: "default",
			});
		} else if (
			!state.success &&
			state.error &&
			(!("code" in state) || state.code !== "AUTH_REQUIRED")
		) {
			toast({
				title: "Update Failed",
				description: state.error,
				variant: "destructive",
			});
		}
	}, [state, toast]);

	return (
		<Card className="w-full max-w-md bg-zinc-950/50 backdrop-blur-xl border-white/5 shadow-2xl overflow-hidden">
			<div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500/20 via-blue-500/40 to-blue-500/20" />

			<CardHeader>
				<div className="flex items-center gap-3 mb-2">
					<div className="p-2 bg-blue-500/10 rounded-lg">
						<KeyRound className="h-5 w-5 text-blue-400" strokeWidth={1.5} />
					</div>
					<CardTitle className="text-xl">Rotate Credentials</CardTitle>
				</div>
				<CardDescription className="text-zinc-500">
					Securely update your primary password. Changes are effective immediately across all active
					sessions.
				</CardDescription>
			</CardHeader>

			<CardContent>
				<form action={action} className="space-y-5">
					<div className="space-y-2">
						<Label htmlFor="currentPassword">Current Password</Label>
						<Input
							id="currentPassword"
							name="currentPassword"
							type="password"
							required
							autoComplete="current-password"
							className="bg-black/40 border-white/10 focus:border-blue-500/50 transition-all h-11"
						/>
					</div>

					<div className="h-px bg-white/5 my-2" />

					<div className="space-y-2">
						<Label htmlFor="newPassword">New Password</Label>
						<Input
							id="newPassword"
							name="newPassword"
							type="password"
							required
							autoComplete="new-password"
							className="bg-black/40 border-white/10 focus:border-blue-500/50 transition-all h-11"
						/>
						<p className="text-[10px] text-zinc-600 uppercase tracking-widest font-bold">
							Requirement: 12+ Characters
						</p>
					</div>

					<div className="space-y-2">
						<Label htmlFor="confirmPassword">Confirm New Password</Label>
						<Input
							id="confirmPassword"
							name="confirmPassword"
							type="password"
							required
							autoComplete="new-password"
							className="bg-black/40 border-white/10 focus:border-blue-500/50 transition-all h-11"
						/>
					</div>

					{!state.success && state.error && (
						<div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 flex items-center gap-3 text-xs text-destructive">
							<AlertCircle className="h-4 w-4 shrink-0" />
							<span>{state.error}</span>
						</div>
					)}

					<Button
						type="submit"
						disabled={isPending}
						className="w-full h-12 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl transition-all active:scale-95 shadow-lg shadow-blue-900/20"
					>
						{isPending ? (
							<>
								<Loader2 className="mr-2 h-4 w-4 animate-spin" />
								Updating Vault...
							</>
						) : (
							<>
								<ShieldCheck className="mr-2 h-4 w-4" />
								Update Security Credentials
							</>
						)}
					</Button>
				</form>
			</CardContent>
		</Card>
	);
}
