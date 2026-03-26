import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
	title: "Matrix Chat",
	description: "Matrix Protocol Chat Integration",
};

export default function RootLayout({ children }: { children: ReactNode }) {
	return (
		<html lang="de" suppressHydrationWarning>
			<body>
				<Providers>{children}</Providers>
			</body>
		</html>
	);
}
