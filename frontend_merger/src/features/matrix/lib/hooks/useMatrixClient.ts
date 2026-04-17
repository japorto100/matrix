"use client";

import { MatrixContext } from "@matrix/components/MatrixProvider";
import { useContext } from "react";

/** Gibt den Matrix-Client-Context zurück. Wirft wenn außerhalb MatrixProvider. */
export function useMatrixClient() {
	const ctx = useContext(MatrixContext);
	if (!ctx) throw new Error("useMatrixClient must be used within MatrixProvider");
	return ctx;
}
