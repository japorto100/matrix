// Control subtab pages — /control/overview, /control/sessions, etc.
// URL is source of truth; routing handled in ControlPage via usePathname.
import { ControlPage } from "@/features/control/ControlPage";

export default function ControlSubtabPage() {
	return <ControlPage />;
}
