"use client";

import type { MatrixCredentials } from "@matrix/lib/types";
import { MatrixErrorBoundary } from "./ErrorBoundary";
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
		<MatrixErrorBoundary fallbackTitle="Chat konnte nicht geladen werden">
			<MatrixProvider credentials={credentials}>
				<MatrixChat />
			</MatrixProvider>
		</MatrixErrorBoundary>
	);
}
