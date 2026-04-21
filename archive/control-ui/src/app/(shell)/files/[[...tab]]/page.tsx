// Files subtab pages — /files/overview, /files/documents, /files/audio, etc.
// URL is source of truth; routing handled in FilesPage via usePathname.
import { FilesPage } from "@/features/files/FilesPage";

export default function FilesSubtabPage() {
	return <FilesPage />;
}
