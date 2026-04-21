import { redirect } from "next/navigation";

// Root → Matrix Chat weiterleiten
export default function HomePage() {
	redirect("/matrix");
}
