"use client";

import { useContext } from "react";
import { MatrixContext } from "@/components/matrix/MatrixProvider";

/** Gibt den Matrix-Client-Context zurück. Wirft wenn außerhalb MatrixProvider. */
export function useMatrixClient() {
	const ctx = useContext(MatrixContext);
	if (!ctx) throw new Error("useMatrixClient must be used within MatrixProvider");
	return ctx;
}
