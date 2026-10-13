import { AppShell } from "@/components/app-shell";
import { ChatHome } from "@/features/chat-home/chat-home";

// The old address of the home screen. Sign-in links still land here, with the
// sign-in code in the URL, so it shows the home screen instead of redirecting.
export default function TodayPage() {
  return (
    <AppShell active="Home">
      <ChatHome />
    </AppShell>
  );
}
