"use client";

import { createAsyncSearch } from "@matrix/lib/asyncSearch";
import { type MemberInfo, roleLabel } from "@matrix/lib/hooks/useRoomMembers";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Ban, Search, UserMinus, X } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";

type SortMode = "power" | "name" | "userId";

interface Props {
	members: MemberInfo[];
	myUserId: string;
	myPowerLevel: number;
	onKick: (userId: string) => void;
	onBan: (userId: string) => void;
}

const VIRTUALIZE_THRESHOLD = 30;
const ROW_HEIGHT = 40;

const searchMembers = createAsyncSearch<MemberInfo>({
	searchFields: (m) => [m.displayName, m.userId],
});

function sortMembers(members: MemberInfo[], mode: SortMode): MemberInfo[] {
	const copy = [...members];
	if (mode === "power") {
		copy.sort((a, b) => {
			if (b.powerLevel !== a.powerLevel) return b.powerLevel - a.powerLevel;
			return a.displayName.localeCompare(b.displayName);
		});
	} else if (mode === "name") {
		copy.sort((a, b) => a.displayName.localeCompare(b.displayName));
	} else {
		copy.sort((a, b) => a.userId.localeCompare(b.userId));
	}
	return copy;
}

export function MemberList({ members, myUserId, myPowerLevel, onKick, onBan }: Props) {
	const [banConfirmId, setBanConfirmId] = useState<string | null>(null);
	const [query, setQuery] = useState("");
	const [sortMode, setSortMode] = useState<SortMode>("power");
	const scrollRef = useRef<HTMLDivElement>(null);

	const filteredAndSorted = useMemo(() => {
		const filtered = searchMembers(query, members);
		return sortMembers(filtered, sortMode);
	}, [members, query, sortMode]);

	const virtualize = filteredAndSorted.length > VIRTUALIZE_THRESHOLD;

	const virtualizer = useVirtualizer({
		count: filteredAndSorted.length,
		getScrollElement: () => scrollRef.current,
		estimateSize: () => ROW_HEIGHT,
		overscan: 5,
		enabled: virtualize,
	});

	const renderMember = (member: MemberInfo) => {
		const memberInitials = member.displayName.slice(0, 2).toUpperCase();
		const isMe = member.userId === myUserId;
		const canModerate = myPowerLevel >= 50 && !isMe && member.powerLevel < myPowerLevel;
		return (
			<div
				className="flex items-center gap-2.5 px-2 py-1.5 rounded-md hover:bg-muted/50 transition-colors group/member"
				style={virtualize ? { height: ROW_HEIGHT } : undefined}
			>
				<Avatar className="h-7 w-7 shrink-0">
					{member.avatarUrl && <AvatarImage src={member.avatarUrl} alt={member.displayName} />}
					<AvatarFallback className="text-[10px] font-semibold bg-muted text-muted-foreground">
						{memberInitials}
					</AvatarFallback>
				</Avatar>
				<div className="flex-1 min-w-0">
					<p className="text-sm font-medium truncate">{member.displayName}</p>
					<p className="text-[10px] text-muted-foreground truncate">{member.userId}</p>
				</div>
				{member.powerLevel > 0 && (
					<Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 shrink-0">
						{roleLabel(member.powerLevel)}
					</Badge>
				)}
				{canModerate && (
					<div className="flex items-center gap-0.5 opacity-0 group-hover/member:opacity-100 transition-opacity shrink-0">
						{banConfirmId === member.userId ? (
							<div className="flex items-center gap-1">
								<span className="text-[10px] text-destructive">Sperren?</span>
								<Button
									variant="ghost"
									size="icon"
									className="h-6 w-6"
									onClick={() => setBanConfirmId(null)}
								>
									<X className="h-3 w-3" />
								</Button>
								<Button
									variant="ghost"
									size="icon"
									className="h-6 w-6 text-destructive hover:bg-destructive/20"
									onClick={() => {
										onBan(member.userId);
										setBanConfirmId(null);
									}}
								>
									<Ban className="h-3 w-3" />
								</Button>
							</div>
						) : (
							<>
								<Button
									variant="ghost"
									size="icon"
									className="h-6 w-6 text-muted-foreground hover:text-foreground"
									onClick={() => onKick(member.userId)}
									title="Entfernen"
								>
									<UserMinus className="h-3 w-3" />
								</Button>
								<Button
									variant="ghost"
									size="icon"
									className="h-6 w-6 text-muted-foreground hover:text-destructive"
									onClick={() => setBanConfirmId(member.userId)}
									title="Sperren"
								>
									<Ban className="h-3 w-3" />
								</Button>
							</>
						)}
					</div>
				)}
			</div>
		);
	};

	return (
		<div className="flex flex-col gap-2">
			<div className="flex items-center justify-between">
				<label className="text-xs font-medium text-muted-foreground">
					Mitglieder ({filteredAndSorted.length}/{members.length})
				</label>
				<Select value={sortMode} onValueChange={(v) => setSortMode(v as SortMode)}>
					<SelectTrigger className="h-7 w-[140px] text-xs">
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						<SelectItem value="power">Nach Rolle</SelectItem>
						<SelectItem value="name">Nach Name</SelectItem>
						<SelectItem value="userId">Nach User-ID</SelectItem>
					</SelectContent>
				</Select>
			</div>

			<div className="relative">
				<Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
				<Input
					type="text"
					placeholder="Mitglieder suchen…"
					value={query}
					onChange={(e) => setQuery(e.target.value)}
					className="h-8 text-xs pl-8"
				/>
			</div>

			{virtualize ? (
				<div ref={scrollRef} className="max-h-[360px] overflow-y-auto">
					<div
						style={{
							height: virtualizer.getTotalSize(),
							width: "100%",
							position: "relative",
						}}
					>
						{virtualizer.getVirtualItems().map((vRow) => {
							const member = filteredAndSorted[vRow.index];
							if (!member) return null;
							return (
								<div
									key={member.userId}
									style={{
										position: "absolute",
										top: 0,
										left: 0,
										width: "100%",
										transform: `translateY(${vRow.start}px)`,
									}}
								>
									{renderMember(member)}
								</div>
							);
						})}
					</div>
				</div>
			) : (
				<div className="flex flex-col gap-1.5">
					{filteredAndSorted.map((member) => (
						<div key={member.userId}>{renderMember(member)}</div>
					))}
				</div>
			)}
		</div>
	);
}
