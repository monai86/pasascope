import type { Metadata } from "next";

import { fontVariables } from "@/app/fonts";
import { Providers } from "@/app/providers";
import { SupabaseAuthRuntimeBridge } from "@/components/supabase-auth-runtime-bridge";
import { getRequestLocale } from "@/i18n/server";
import "@/styles/globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL?.trim() || "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "PasaScope | Thai Pediatric Speech-Language Assessment",
  description: "PasaScope (ภาษา-สโคป) — Clinical decision-support platform for Thai pediatric speech-language therapist review workflows."
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getRequestLocale();

  return (
    <html lang={locale} className={fontVariables}>
      <body>
        <Providers initialLocale={locale}>
          <SupabaseAuthRuntimeBridge />
          {children}
        </Providers>
      </body>
    </html>
  );
}
