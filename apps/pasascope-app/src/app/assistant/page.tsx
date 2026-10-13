import { redirect } from "next/navigation";

// The assistant has no screen of its own; the home screen answers questions.
export default function AssistantPage() {
  redirect("/");
}
