/**
 * A2UI Provider — Google A2UI v0.9 via @copilotkit/a2ui-renderer
 *
 * Wraps the app tree so any component can mount an <A2UIRenderer /> and
 * receive streamed widget-messages from the python-agent (via SSE).
 *
 * SOTA setup (direct catalog prop — not config wrapper):
 *   - basicCatalog: Google primitives (Text, Image, Button, Card, Row, Column,
 *     Tabs, Modal, TextField, CheckBox, Slider, DateTimeInput, …)
 *   - Custom catalog-extension planned for ChartWidget + PortfolioCard
 *     via createReactComponent + createA2UICatalog (once backend streams widgets).
 *
 * Data-flow (once backend wired):
 *   python-agent (a2ui-agent-sdk) → SSE /api/agent/chat
 *     → MessageProcessor → A2UI store → A2UIRenderer mounts Surface → widgets
 *
 * License: @a2ui/react + @a2ui/web_core + @copilotkit/a2ui-renderer = MIT/Apache-2.0,
 * self-host free, no cloud API calls.
 */

"use client";

import { A2UIProvider, basicCatalog } from "@copilotkit/a2ui-renderer";
import type { ReactNode } from "react";

interface A2uiProviderProps {
	children: ReactNode;
}

export function A2uiRootProvider({ children }: A2uiProviderProps) {
	return <A2UIProvider catalog={basicCatalog}>{children}</A2UIProvider>;
}
