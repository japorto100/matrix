"use client";

import data from "@emoji-mart/data";
import Picker from "@emoji-mart/react";

interface Props {
	onSelect: (emoji: string) => void;
}

export function EmojiPicker({ onSelect }: Props) {
	return (
		<Picker
			data={data}
			onEmojiSelect={(emoji: { native: string }) => onSelect(emoji.native)}
			theme="dark"
			locale="de"
			previewPosition="none"
			skinTonePosition="search"
			maxFrequentRows={2}
			perLine={8}
		/>
	);
}
