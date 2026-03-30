"use client";

import { useEffect } from "react";

interface KeyboardShortcutHandlers {
	/** Ctrl+K → Room Quick Switcher */
	onQuickSwitch?: () => void;
	/** Escape → Panel/Dialog schliessen */
	onEscape?: () => void;
	/** Pfeil-Oben im leeren Composer → letzte eigene Nachricht editieren */
	onEditLastMessage?: () => void;
}

/**
 * Hook fuer Matrix Chat Keyboard Shortcuts.
 * Registriert globale Keydown-Listener innerhalb des Matrix Chat Kontexts.
 *
 * Shortcuts:
 * - Ctrl+K: Room Quick Switcher (nur wenn MatrixChat fokussiert)
 * - Esc: Aktives Panel schliessen
 * - Arrow Up (im leeren Composer): Letzte eigene Nachricht editieren
 */
export function useKeyboardShortcuts({
	onQuickSwitch,
	onEscape,
	onEditLastMessage,
}: KeyboardShortcutHandlers) {
	useEffect(() => {
		function handleKeyDown(e: KeyboardEvent) {
			// Ctrl+K → Quick Switcher
			if ((e.ctrlKey || e.metaKey) && e.key === "k") {
				// Nur wenn wir im Matrix-Chat-Bereich sind (pruefen ob ein Matrix-Element fokussiert ist)
				const active = document.activeElement;
				const isInMatrix =
					active?.closest("[data-matrix-chat]") !== null ||
					document.querySelector("[data-matrix-chat]:hover") !== null;
				if (isInMatrix && onQuickSwitch) {
					e.preventDefault();
					onQuickSwitch();
				}
			}

			// Escape → Panel schliessen
			if (e.key === "Escape" && onEscape) {
				// Nicht wenn ein Dialog offen ist (shadcn Dialog handled Esc selbst)
				const hasOpenDialog = document.querySelector("[role='dialog'][data-state='open']");
				if (!hasOpenDialog) {
					onEscape();
				}
			}

			// Pfeil-Oben → Letzte Nachricht editieren
			if (e.key === "ArrowUp" && onEditLastMessage) {
				const target = e.target as HTMLElement;
				// Nur wenn im Textarea/Input und leer
				if (
					(target.tagName === "TEXTAREA" || target.tagName === "INPUT") &&
					(target as HTMLTextAreaElement | HTMLInputElement).value === ""
				) {
					e.preventDefault();
					onEditLastMessage();
				}
			}
		}

		document.addEventListener("keydown", handleKeyDown);
		return () => document.removeEventListener("keydown", handleKeyDown);
	}, [onQuickSwitch, onEscape, onEditLastMessage]);
}
