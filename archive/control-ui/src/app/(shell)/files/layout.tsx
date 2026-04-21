import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
	title: "Files",
	description:
		"Document and media surface: PDF, audio, video, data files, images, and alternative data.",
};

export default function FilesLayout({ children }: { children: ReactNode }) {
	return <div className="h-screen overflow-hidden">{children}</div>;
}
