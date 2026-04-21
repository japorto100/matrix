"use client";

import { ClientEvent, type MatrixClient, type MatrixEvent } from "matrix-js-sdk";
import { useEffect, useRef, useState } from "react";

/**
 * Liest m.account_data eines bestimmten eventType reactive.
 *
 * Initial-Load: Content aus client.getAccountData() (frischer Snapshot).
 * Updates: Listener auf ClientEvent.AccountData, filtert nach eventType.
 *
 * Fehlertoleranz: getContent-Parse-Fehler werden geschluckt (kein Tree-Crash),
 * nur console.warn. State bleibt auf letztem bekannten Wert.
 *
 * Gateway-Hook fuer SecretStorage, KeyBackup, IgnoredUsers, m.direct, PushRules.
 */
export function useAccountData<T = unknown>(
	client: MatrixClient | null,
	eventType: string,
): T | undefined {
	const [content, setContent] = useState<T | undefined>(() => {
		if (!client) return undefined;
		try {
			// SDK 41 typed getAccountData auf `keyof AccountDataEvents`, Matrix-Spec erlaubt
			// aber custom eventTypes (z.B. `m.secret_storage.default_key`, app-spezifische Keys).
			// Cast ist korrekt — SDK macht keinen Type-Level-Filter auf unknown keys.
			const initial = client.getAccountData(eventType as unknown as never)?.getContent() as
				| T
				| undefined;
			return initial ?? undefined;
		} catch (err) {
			console.warn(`[useAccountData] initial read failed for ${eventType}:`, err);
			return undefined;
		}
	});

	useEffect(() => {
		if (!client) return;
		// Re-Sync bei eventType-Wechsel: initial-state neu lesen, sonst zeigt der Hook
		// den stale Wert des vorherigen eventType bis der erste AccountData-Event kommt.
		try {
			const fresh = client.getAccountData(eventType as unknown as never)?.getContent() as
				| T
				| undefined;
			setContent(fresh ?? undefined);
		} catch (err) {
			console.warn(`[useAccountData] re-sync read failed for ${eventType}:`, err);
		}
		const handler = (evt: MatrixEvent) => {
			if (evt.getType() !== eventType) return;
			try {
				setContent((evt.getContent() as T) ?? undefined);
			} catch (err) {
				console.warn(`[useAccountData] update parse failed for ${eventType}:`, err);
			}
		};
		client.on(ClientEvent.AccountData, handler);
		return () => {
			client.off(ClientEvent.AccountData, handler);
		};
	}, [client, eventType]);

	return content;
}

/**
 * Generischer Listener fuer m.account_data events (alle Types).
 *
 * Nutzt Ref-Pattern damit Callback-Identity-Changes keine Re-Subscription
 * ausloesen — Consumer muss callback nicht mit useCallback wrappen.
 */
export function useAccountDataCallback(
	client: MatrixClient | null,
	callback: (evt: MatrixEvent) => void,
): void {
	const callbackRef = useRef(callback);
	useEffect(() => {
		callbackRef.current = callback;
	}, [callback]);

	useEffect(() => {
		if (!client) return;
		const handler = (evt: MatrixEvent) => callbackRef.current(evt);
		client.on(ClientEvent.AccountData, handler);
		return () => {
			client.off(ClientEvent.AccountData, handler);
		};
	}, [client]);
}
