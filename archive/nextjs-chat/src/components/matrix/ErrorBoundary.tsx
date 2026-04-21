"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

interface Props {
	children: ReactNode;
	fallbackTitle?: string;
}

interface State {
	hasError: boolean;
	error: Error | null;
}

export class MatrixErrorBoundary extends Component<Props, State> {
	constructor(props: Props) {
		super(props);
		this.state = { hasError: false, error: null };
	}

	static getDerivedStateFromError(error: Error): State {
		return { hasError: true, error };
	}

	componentDidCatch(error: Error, errorInfo: ErrorInfo) {
		console.error("[MatrixErrorBoundary]", error, errorInfo);
	}

	render() {
		if (this.state.hasError) {
			return (
				<div className="flex flex-col items-center justify-center h-full gap-4 p-8 text-center">
					<div className="flex items-center justify-center h-12 w-12 rounded-full bg-destructive/10">
						<AlertTriangle className="h-6 w-6 text-destructive" />
					</div>
					<div>
						<h2 className="text-sm font-semibold mb-1">
							{this.props.fallbackTitle ?? "Etwas ist schiefgelaufen"}
						</h2>
						<p className="text-xs text-muted-foreground max-w-sm">
							{this.state.error?.message ?? "Ein unerwarteter Fehler ist aufgetreten."}
						</p>
					</div>
					<Button
						variant="outline"
						size="sm"
						onClick={() => this.setState({ hasError: false, error: null })}
						className="gap-2"
					>
						<RefreshCw className="h-3.5 w-3.5" />
						Neu laden
					</Button>
				</div>
			);
		}

		return this.props.children;
	}
}
