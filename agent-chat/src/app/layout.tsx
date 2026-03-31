import type { Metadata } from "next";
import "./globals.css";
import "@/lib/webmcp-polyfill";
import { Toaster } from "sonner";

export const metadata: Metadata = {
	title: "Agent Chat — Isolated Dev",
	description: "Agent Chat UI isolated development environment",
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="en" suppressHydrationWarning>
			<body className="dark antialiased bg-background text-foreground">
				{children}
				<Toaster />
			</body>
		</html>
	);
}
