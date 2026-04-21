"use client";

import { Ban, UserMinus, X } from "lucide-react";
import { useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { type MemberInfo, roleLabel } from "@/lib/matrix/hooks/useRoomMembers";

interface Props {
	members: MemberInfo[];
	myUserId: string;
	myPowerLevel: number;
	onKick: (userId: string) => void;
	onBan: (userId: string) => void;
}

export function MemberList({ members, myUserId, myPowerLevel, onKick, onBan }: Props) {
	const [banConfirmId, setBanConfirmId] = useState<string | null>(null);

	return (
		<div>
			<label className="text-xs font-medium text-muted-foreground mb-2 block">
				Mitglieder ({members.length})
			</label>
			<div className="flex flex-col gap-1.5">
				{members.map((member) => {
					const memberInitials = member.displayName.slice(0, 2).toUpperCase();
					const isMe = member.userId === myUserId;
					const canModerate = myPowerLevel >= 50 && !isMe && member.powerLevel < myPowerLevel;
					return (
						<div
							key={member.userId}
							className="flex items-center gap-2.5 px-2 py-1.5 rounded-md hover:bg-muted/50 transition-colors group/member"
						>
							<Avatar className="h-7 w-7 shrink-0">
								{member.avatarUrl && (
									<AvatarImage src={member.avatarUrl} alt={member.displayName} />
								)}
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
				})}
			</div>
		</div>
	);
}
