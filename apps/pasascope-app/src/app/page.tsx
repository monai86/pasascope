import { redirect } from "next/navigation";

import { WorkQueueDashboard } from "@/components/work-queue-dashboard";

// The workbench's home is Today. With the chat shell built in, `/` is the
// home itself: the chat home when the API runs the public workflow, and the
// Today queue otherwise.
export default function Home() {
  if (process.env.NEXT_PUBLIC_CHAT_SHELL !== "true") redirect("/today");
  return <WorkQueueDashboard active="Today" />;
}
