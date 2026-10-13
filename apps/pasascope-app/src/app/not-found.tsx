import { Compass } from "lucide-react";

import { routeStateMessages } from "@/app/route-states.messages";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { getMessages } from "@/i18n/server";

export default async function NotFound() {
  const t = (await getMessages(routeStateMessages)).notFound;

  return (
    <main className="app-canvas flex min-h-dvh items-center justify-center p-4">
      <EmptyState
        className="w-full max-w-xl shadow-lift"
        icon={Compass}
        title={t.title}
        description={t.description}
        action={
          <>
            <Button href="/">{t.goToHome}</Button>
            <Button href="/cases" variant="secondary">{t.goToCases}</Button>
          </>
        }
      />
    </main>
  );
}
