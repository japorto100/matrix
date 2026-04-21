"use client";

// AC48b: Mic device selector — enumerates audio input devices
// Extracted from AgentChatComposer.tsx

import { useEffect, useState } from "react";

export function useMicDevices() {
	const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
	const [selectedId, setSelectedId] = useState<string | undefined>();

	useEffect(() => {
		if (typeof navigator?.mediaDevices?.enumerateDevices !== "function") return;
		void navigator.mediaDevices
			.enumerateDevices()
			.then((devs) => {
				const inputs = devs.filter((d) => d.kind === "audioinput");
				setDevices(inputs);
				const def = inputs.find((d) => d.deviceId === "default") ?? inputs[0];
				if (def) setSelectedId(def.deviceId);
			})
			.catch(() => {});
	}, []);

	return { devices, selectedId, setSelectedId };
}
