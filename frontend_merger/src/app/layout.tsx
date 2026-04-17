import type { Metadata } from "next";
import { DM_Sans, Geist_Mono } from "next/font/google";
import type { ReactNode } from "react";
import { Toaster } from "sonner";
import "@agent/lib/webmcp-polyfill";
import { GlobalChatOverlay } from "@agent/components/GlobalChatOverlay";
import { AgentProviders } from "@agent/providers/AgentProviders";
import { GlobalTopBar } from "@/components/GlobalTopBar";
import { Providers } from "@/components/providers";
import "./globals.css";

const dmSans = DM_Sans({
	variable: "--font-dm-sans",
	subsets: ["latin"],
	display: "swap",
});

const geistMono = Geist_Mono({
	variable: "--font-geist-mono",
	subsets: ["latin"],
	display: "swap",
});

export const metadata: Metadata = {
	title: "Matrix · Frontend Merger",
	description:
		"Unified shell that mounts Matrix Chat, Agent Chat and Control UI. Test harness for tradeview-fusion integration.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
	return (
		<html lang="en" suppressHydrationWarning className={`${dmSans.variable} ${geistMono.variable}`}>
			<body className="dark antialiased bg-background text-foreground font-sans">
				<Providers>
					<AgentProviders>
						<div className="flex h-screen flex-col">
							<GlobalTopBar />
							<main className="flex-1 overflow-hidden">{children}</main>
						</div>
						<GlobalChatOverlay />
					</AgentProviders>
				</Providers>
				<Toaster
					theme="dark"
					position="bottom-right"
					toastOptions={{
						className: "bg-card border-border text-foreground",
					}}
				/>
			</body>
		</html>
	);
}
