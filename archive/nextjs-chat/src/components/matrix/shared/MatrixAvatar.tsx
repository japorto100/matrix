"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { hashColor, mxcToHttp } from "@/lib/matrix/utils";
import { cn } from "@/lib/utils";

const BG_COLORS = [
	"bg-blue-600",
	"bg-emerald-600",
	"bg-violet-600",
	"bg-amber-600",
	"bg-rose-600",
	"bg-cyan-600",
	"bg-indigo-600",
	"bg-pink-600",
];

const SIZES = {
	xs: "h-6 w-6 text-[10px]",
	sm: "h-8 w-8 text-xs",
	md: "h-9 w-9 text-sm",
	lg: "h-[72px] w-[72px] text-lg",
	xl: "h-20 w-20 text-xl",
} as const;

interface MatrixAvatarProps {
	/** MXC URL (mxc://...) oder HTTP URL oder undefined */
	mxcUrl?: string;
	/** Name fuer Initials + Farbe */
	name: string;
	/** Groesse */
	size?: keyof typeof SIZES;
	/** Online-Indikator (gruener Dot) */
	isOnline?: boolean;
	/** Bot-Styling */
	isBot?: boolean;
	/** Zusaetzliche CSS-Klassen auf Avatar */
	className?: string;
}

export function MatrixAvatar({
	mxcUrl,
	name,
	size = "md",
	isOnline,
	isBot,
	className,
}: MatrixAvatarProps) {
	const src = mxcUrl?.startsWith("mxc://") ? mxcToHttp(mxcUrl) : mxcUrl;
	const initials = name.slice(0, 2).toUpperCase() || "?";
	const bgColor = isBot ? "bg-primary/20 text-primary" : hashColor(name, BG_COLORS);

	return (
		<div className="relative shrink-0">
			<Avatar className={cn(SIZES[size], className)}>
				{src && <AvatarImage src={src} alt={name} />}
				<AvatarFallback className={cn("font-semibold text-white", bgColor)}>
					{initials}
				</AvatarFallback>
			</Avatar>
			{isOnline && (
				<span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-background" />
			)}
		</div>
	);
}
