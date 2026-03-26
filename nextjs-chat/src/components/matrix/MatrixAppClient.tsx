"use client";

import type { MatrixCredentials } from "@/lib/matrix/types";
import { MatrixChat } from "./MatrixChat";
import { MatrixProvider } from "./MatrixProvider";

interface Props {
	credentials: MatrixCredentials;
}

/**
 * Client-seitiger Einstiegspunkt für die Matrix-Chat-App.
 * Wird via dynamic(ssr:false) geladen — darf kein Server-Code enthalten.
 */
export function MatrixAppClient({ credentials }: Props) {
	return (
		<MatrixProvider credentials={credentials}>
			<MatrixChat />
		</MatrixProvider>
	);
}
