"use client";

import { lazy } from "react";
import type { MatrixCredentials } from "@/lib/matrix/types";

// React.lazy statt next/dynamic — matrix-js-sdk ist Browser-only
const MatrixAppClient = lazy(() =>
	import("@/components/matrix/MatrixAppClient").then((m) => ({
		default: m.MatrixAppClient,
	})),
);

interface Props {
	credentials: MatrixCredentials;
}

export function MatrixLoader({ credentials }: Props) {
	return <MatrixAppClient credentials={credentials} />;
}
