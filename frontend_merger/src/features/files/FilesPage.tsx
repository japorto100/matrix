"use client";

// Files Page — Phase 22b (DW1-DW4)
// Shell: top nav + tab routing. URL is source of truth.
// Tabs: overview | documents | audio | video | data | images | uploads

import { usePathname } from "next/navigation";
import { FilesAudioTab } from "./components/FilesAudioTab";
import { FilesDataTab } from "./components/FilesDataTab";
import { FilesDocumentsTab } from "./components/FilesDocumentsTab";
import { FilesImagesTab } from "./components/FilesImagesTab";
import { FilesOverviewTab } from "./components/FilesOverviewTab";
import { FilesTopNav } from "./components/FilesTopNav";
import { FilesUploadsTab } from "./components/FilesUploadsTab";
import { FilesVideoTab } from "./components/FilesVideoTab";

export function FilesPage() {
	const pathname = usePathname();

	const renderTab = () => {
		if (pathname === "/files" || pathname === "/files/overview") {
			return <FilesOverviewTab />;
		}
		if (pathname === "/files/documents") {
			return <FilesDocumentsTab />;
		}
		if (pathname === "/files/audio") {
			return <FilesAudioTab />;
		}
		if (pathname === "/files/video") {
			return <FilesVideoTab />;
		}
		if (pathname === "/files/data") {
			return <FilesDataTab />;
		}
		if (pathname === "/files/images") {
			return <FilesImagesTab />;
		}
		if (pathname === "/files/uploads") {
			return <FilesUploadsTab />;
		}
		return <FilesOverviewTab />;
	};

	return (
		<div className="flex h-full flex-col bg-background">
			<FilesTopNav />
			<div className="flex flex-1 flex-col overflow-y-auto">{renderTab()}</div>
		</div>
	);
}
