import { AppShell } from "@/components/app-shell";
import { ChatHome } from "@/features/chat-home/chat-home";

// `/` is the home screen: it asks what to do and answers typed questions.
export default function Home() {
  return (
    <AppShell active="Home">
      <ChatHome />
    </AppShell>
  );
}
