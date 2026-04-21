"use client";

import { FeatureCheck } from "@matrix/components/FeatureCheck";
import type { MatrixCredentials } from "@matrix/lib/types";
import { lazy } from "react";

// React.lazy statt next/dynamic — matrix-js-sdk ist Browser-only
const MatrixAppClient = lazy(() =>
	import("@matrix/components/MatrixAppClient").then((m) => ({
		default: m.MatrixAppClient,
	})),
);

interface Props {
	credentials: MatrixCredentials;
}

export function MatrixLoader({ credentials }: Props) {
	return (
		<FeatureCheck>
			<MatrixAppClient credentials={credentials} />
		</FeatureCheck>
	);
}
