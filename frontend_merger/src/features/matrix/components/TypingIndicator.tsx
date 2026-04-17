"use client";

import { AnimatePresence, motion } from "motion/react";

interface Props {
	typers: string[];
}

export function TypingIndicator({ typers }: Props) {
	if (typers.length === 0) return null;

	const label =
		typers.length === 1
			? `${typers[0]} tippt…`
			: `${typers.slice(0, -1).join(", ")} und ${typers.at(-1)} tippen…`;

	return (
		<AnimatePresence>
			<motion.div
				key="typing"
				initial={{ opacity: 0, y: 4 }}
				animate={{ opacity: 1, y: 0 }}
				exit={{ opacity: 0, y: 4 }}
				className="flex items-center gap-2 px-4 py-1 text-xs text-muted-foreground"
			>
				{/* Animierte Punkte */}
				<span className="flex gap-0.5">
					{[0, 1, 2].map((i) => (
						<motion.span
							key={i}
							className="inline-block w-1 h-1 rounded-full bg-muted-foreground"
							animate={{ y: [0, -4, 0] }}
							transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
						/>
					))}
				</span>
				<span>{label}</span>
			</motion.div>
		</AnimatePresence>
	);
}
