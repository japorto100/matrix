import { Suspense } from "react";
import type { MatrixCredentials } from "@/lib/matrix/types";
import { MatrixLoader } from "./MatrixLoader";

/** Credentials werden server-seitig aus env gelesen — kein Client-Fetch nötig. */
async function getCredentials(): Promise<MatrixCredentials | null> {
	const homeserverUrl = process.env.MATRIX_HOMESERVER_URL;
	const userId = process.env.MATRIX_USER_ID;
	const accessToken = process.env.MATRIX_ACCESS_TOKEN;
	const deviceId = process.env.MATRIX_DEVICE_ID;

	if (!homeserverUrl || !userId || !accessToken) return null;
	return { homeserverUrl, userId, accessToken, deviceId };
}

export default async function MatrixPage() {
	const credentials = await getCredentials();

	if (!credentials) {
		return (
			<div className="flex items-center justify-center h-full">
				<div className="text-center max-w-md space-y-3">
					<h2 className="font-semibold text-lg">Matrix nicht konfiguriert</h2>
					<p className="text-sm text-muted-foreground">
						Lege{" "}
						<code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">.env.local</code>{" "}
						an mit:
					</p>
					<pre className="text-xs bg-muted p-4 rounded-md text-left leading-relaxed">
						{`MATRIX_HOMESERVER_URL=http://localhost:8448
MATRIX_USER_ID=@alice:matrix.local
MATRIX_ACCESS_TOKEN=syt_...
MATRIX_DEVICE_ID=ABCDE`}
					</pre>
				</div>
			</div>
		);
	}

	return (
		<div className="h-screen flex flex-col">
			<Suspense
				fallback={
					<div className="flex items-center justify-center h-full text-sm text-muted-foreground">
						Lade Matrix…
					</div>
				}
			>
				<MatrixLoader credentials={credentials} />
			</Suspense>
		</div>
	);
}
