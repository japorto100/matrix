"use client";

import { KeyRound, LogOut, SlidersHorizontal, User } from "lucide-react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { PasswordChangePanel } from "@/features/settings/PasswordChangePanel";
import { isAuthEnabled } from "@/lib/auth/runtime-flags";
import { signOutAndBroadcast } from "@/lib/auth/sign-out";

export function UserMenuButton() {
	const { data: session } = useSession();
	const [isSigningOut, setIsSigningOut] = useState(false);
	const [pwDialogOpen, setPwDialogOpen] = useState(false);
	const authEnabled = isAuthEnabled();

	if (!authEnabled) return null;

	if (!session?.user) {
		return (
			<Button
				variant="outline"
				size="sm"
				className="h-7 text-[11px] uppercase font-black tracking-widest gap-1.5"
				asChild
			>
				<Link href="/auth/sign-in">
					<User className="h-3 w-3" />
					Sign In
				</Link>
			</Button>
		);
	}

	return (
		<>
			<DropdownMenu>
				<DropdownMenuTrigger asChild>
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7"
						aria-label="Account menu"
						data-testid="header-account-menu"
					>
						<User className="h-3.5 w-3.5" />
					</Button>
				</DropdownMenuTrigger>
				<DropdownMenuContent align="end" className="w-56">
					<div className="flex items-center justify-start gap-2 p-2">
						<div className="flex flex-col space-y-0.5 leading-none">
							{session.user.name && <p className="font-medium text-xs">{session.user.name}</p>}
							{session.user.email && (
								<p className="w-[200px] truncate text-[11px] text-muted-foreground uppercase tracking-wider font-bold">
									{session.user.email}
								</p>
							)}
						</div>
					</div>
					<Separator className="my-1 opacity-50" />
					<DropdownMenuItem className="cursor-pointer" onSelect={() => setPwDialogOpen(true)}>
						<KeyRound className="mr-2 h-4 w-4" />
						<span>Change Password</span>
					</DropdownMenuItem>
					<DropdownMenuItem asChild>
						<Link href="/settings" className="cursor-pointer">
							<User className="mr-2 h-4 w-4" />
							<span>Settings</span>
						</Link>
					</DropdownMenuItem>
					{session.user.role === "admin" && (
						<DropdownMenuItem asChild>
							<Link href="/admin/users" className="cursor-pointer">
								<SlidersHorizontal className="mr-2 h-4 w-4" />
								<span>Admin</span>
							</Link>
						</DropdownMenuItem>
					)}
					<Separator className="my-1 opacity-50" />
					<DropdownMenuItem
						data-testid="header-signout"
						disabled={isSigningOut}
						className="text-destructive focus:text-destructive cursor-pointer"
						onSelect={async (event) => {
							event.preventDefault();
							setIsSigningOut(true);
							try {
								await signOutAndBroadcast({ callbackUrl: "/auth/sign-in" });
							} finally {
								setIsSigningOut(false);
							}
						}}
					>
						<LogOut className="mr-2 h-4 w-4" />
						<span>{isSigningOut ? "Signing out..." : "Sign Out"}</span>
					</DropdownMenuItem>
				</DropdownMenuContent>
			</DropdownMenu>
			<Dialog open={pwDialogOpen} onOpenChange={setPwDialogOpen}>
				<DialogContent className="max-w-lg">
					<DialogHeader>
						<DialogTitle>Change Password</DialogTitle>
						<DialogDescription>Enter your current password and choose a new one.</DialogDescription>
					</DialogHeader>
					<PasswordChangePanel />
				</DialogContent>
			</Dialog>
		</>
	);
}
