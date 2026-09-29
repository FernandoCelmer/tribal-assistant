import type { ReactNode } from "react";
import { BottomNav } from "@/components/layout/bottom-nav";
import { LiveRefresh } from "@/components/layout/live-refresh";
import { PageTransition } from "@/components/layout/page-transition";
import { Sidebar } from "@/components/layout/sidebar";
import { DialogHost } from "@/components/ui/dialog-host";
import { Toaster } from "@/components/ui/toast";
import { accounts, apiVersion } from "@/lib/session";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const [{ list, current }, api] = await Promise.all([accounts(), apiVersion()]);
  const versions = { web: process.env.WEB_VERSION ?? "—", api };

  return (
    <div className="min-h-screen bg-background">
      <Sidebar versions={versions} accounts={list} current={current} />
      <main className="min-h-screen pb-[calc(88px+env(safe-area-inset-bottom))] md:ml-[280px] md:pb-0 xl:ml-[304px]">
        <div className="w-full px-4 py-5 md:px-8 md:py-8 xl:px-9 xl:pt-9 xl:pb-16">
          <PageTransition>{children}</PageTransition>
        </div>
      </main>
      <BottomNav />
      <Toaster />
      <DialogHost />
      <LiveRefresh />
    </div>
  );
}
