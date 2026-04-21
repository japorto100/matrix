"use client";

import { Bell, Info, Monitor, Smartphone, User } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AboutTab } from "./app-settings/AboutTab";
import { AccountTab } from "./app-settings/AccountTab";
import { AppearanceTab } from "./app-settings/AppearanceTab";
import { DevicesTab } from "./app-settings/DevicesTab";
import { NotificationsTab } from "./app-settings/NotificationsTab";

interface Props {
	client: MatrixClient;
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

/**
 * G3 AppSettingsSheet — globaler Settings-Sheet fuer den Matrix-Client.
 *
 * Trigger: "Einstellungen"-Link im UserProfileDialog (NICHT direkt am Avatar
 * — der Avatar-Click oeffnet weiterhin den Profile-Dialog).
 *
 * 5 Tabs: Account, Erscheinungsbild, Benachrichtigungen, Geraete, Info.
 */
export function AppSettingsSheet({ client, open, onOpenChange }: Props) {
	return (
		<Sheet open={open} onOpenChange={onOpenChange}>
			<SheetContent className="sm:max-w-lg w-full p-0 flex flex-col overflow-hidden">
				<SheetHeader className="p-4 border-b shrink-0">
					<SheetTitle>Einstellungen</SheetTitle>
				</SheetHeader>

				<Tabs defaultValue="account" className="flex-1 flex flex-col overflow-hidden">
					<TabsList className="shrink-0 w-full justify-start rounded-none h-10 border-b bg-background px-2 gap-1">
						<TabsTrigger value="account" className="text-xs h-7">
							<User className="h-3 w-3 mr-1" />
							Konto
						</TabsTrigger>
						<TabsTrigger value="appearance" className="text-xs h-7">
							<Monitor className="h-3 w-3 mr-1" />
							Aussehen
						</TabsTrigger>
						<TabsTrigger value="notifications" className="text-xs h-7">
							<Bell className="h-3 w-3 mr-1" />
							Alerts
						</TabsTrigger>
						<TabsTrigger value="devices" className="text-xs h-7">
							<Smartphone className="h-3 w-3 mr-1" />
							Geraete
						</TabsTrigger>
						<TabsTrigger value="about" className="text-xs h-7">
							<Info className="h-3 w-3 mr-1" />
							Info
						</TabsTrigger>
					</TabsList>

					<TabsContent
						value="account"
						className="flex-1 overflow-y-auto p-4 mt-0 data-[state=inactive]:hidden"
					>
						<AccountTab client={client} />
					</TabsContent>
					<TabsContent
						value="appearance"
						className="flex-1 overflow-y-auto p-4 mt-0 data-[state=inactive]:hidden"
					>
						<AppearanceTab />
					</TabsContent>
					<TabsContent
						value="notifications"
						className="flex-1 overflow-y-auto p-4 mt-0 data-[state=inactive]:hidden"
					>
						<NotificationsTab client={client} />
					</TabsContent>
					<TabsContent
						value="devices"
						className="flex-1 overflow-y-auto p-4 mt-0 data-[state=inactive]:hidden"
					>
						<DevicesTab client={client} />
					</TabsContent>
					<TabsContent
						value="about"
						className="flex-1 overflow-y-auto p-4 mt-0 data-[state=inactive]:hidden"
					>
						<AboutTab client={client} />
					</TabsContent>
				</Tabs>
			</SheetContent>
		</Sheet>
	);
}
