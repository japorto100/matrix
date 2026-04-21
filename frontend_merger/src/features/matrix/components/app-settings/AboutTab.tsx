"use client";

import type { MatrixClient } from "matrix-js-sdk";

interface Props {
	client: MatrixClient;
}

export function AboutTab({ client }: Props) {
	const homeserverUrl = client.getHomeserverUrl();
	const sdkVersion = "matrix-js-sdk ^41.2.0";

	return (
		<div className="space-y-3 text-sm">
			<div>
				<h3 className="font-semibold">App</h3>
				<p className="text-xs text-muted-foreground">frontend_merger (matrix chat)</p>
			</div>
			<div>
				<h3 className="font-semibold">Homeserver</h3>
				<code className="text-xs text-muted-foreground break-all">{homeserverUrl}</code>
			</div>
			<div>
				<h3 className="font-semibold">Matrix SDK</h3>
				<p className="text-xs text-muted-foreground">{sdkVersion}</p>
			</div>
			<div>
				<h3 className="font-semibold">Basiert auf</h3>
				<p className="text-xs text-muted-foreground">
					Next.js 16.2, React 19, React-Query, shadcn/ui. Cinny-Pattern-Inspiration (AGPL-safe,
					eigene Reimplementation).
				</p>
			</div>
			<div className="border-t pt-3">
				<p className="text-[10px] text-muted-foreground">
					Fuer weitere Details siehe <code>specs/execution/exec2-03c-cinny.md</code>.
				</p>
			</div>
		</div>
	);
}
