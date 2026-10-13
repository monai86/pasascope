import { redirect } from "next/navigation";

import { WorkQueueDashboard } from "@/components/work-queue-dashboard";

// `/` is the home screen: the chat home when the API runs the public
// workflow, and the Today queue otherwise. A build that opted out of the chat
// shell keeps the workbench's own rule, where Today is the single home.
export default function Home() {
  if (process.env.NEXT_PUBLIC_CHAT_SHELL === "false") redirect("/today");
  return <WorkQueueDashboard active="Today" />;
}
