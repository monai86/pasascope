import { redirect } from "next/navigation";

// The assistant has no screen of its own: AI-assisted review lives in the
// Session workspace, reached from Today.
export default function AssistantPage() {
  redirect("/today");
}
