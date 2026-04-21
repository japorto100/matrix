// Memory subtab pages — /memory, /memory/timeline, /memory/kg, /memory/ingestion
// URL is source of truth; routing handled in MemoryPage via nuqs + usePathname.

import { MemoryPage } from "@/features/memory/MemoryPage";

export default function MemorySubtabPage() {
	return <MemoryPage />;
}
