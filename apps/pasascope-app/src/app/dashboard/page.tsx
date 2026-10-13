import { redirect } from "next/navigation";

// The practice dashboard is gone; its address leads home.
export default function DashboardPage() {
  redirect("/");
}
