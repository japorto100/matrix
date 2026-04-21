"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface Props {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	readBy: string[];
}

export function ReadByDialog({ open, onOpenChange, readBy }: Props) {
	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-sm">
				<DialogHeader>
					<DialogTitle>Gelesen von</DialogTitle>
				</DialogHeader>

				<div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto">
					{readBy.length === 0 && (
						<p className="text-sm text-muted-foreground text-center py-4">
							Noch von niemandem gelesen.
						</p>
					)}
					{readBy.map((userId) => {
						const initials =
							userId.split(":")[0]?.replace("@", "").slice(0, 2).toUpperCase() ?? "?";
						return (
							<div
								key={userId}
								className="flex items-center gap-2.5 px-2 py-1.5 rounded-md hover:bg-muted/50 transition-colors"
							>
								<Avatar className="h-7 w-7 shrink-0">
									<AvatarFallback className="text-[10px] font-semibold bg-primary/30 text-primary">
										{initials}
									</AvatarFallback>
								</Avatar>
								<span className="text-sm truncate">{userId}</span>
							</div>
						);
					})}
				</div>
			</DialogContent>
		</Dialog>
	);
}
