import type { Metadata } from "next";
import { DM_Sans, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "sonner";
import { Providers } from "@/components/providers";

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
	title: "Matrix · Control UI",
	description: "Memory & Control Surface for Matrix Agent",
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="en" suppressHydrationWarning className={`${dmSans.variable} ${geistMono.variable}`}>
			<body className="dark antialiased bg-background text-foreground font-sans">
				<Providers>{children}</Providers>
				<Toaster />
			</body>
		</html>
	);
}
