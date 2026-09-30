"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { mobileItems, active } from "./nav";
import { useReadOnly } from "./read-only";

export function BottomNav() {
  const pathname = usePathname();
  const items = mobileItems(useReadOnly());
  return (
    <nav aria-label="Principal" className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-sidebar pb-[env(safe-area-inset-bottom)] md:hidden">
      <ul className="grid h-[76px] grid-cols-5">
        {items.map((item) => {
          const Icon = item.icon;
          const isOn = active(pathname, item);
          return (
            <li key={item.href} className="min-w-0">
              <Link href={item.href} aria-current={isOn ? "page" : undefined} className={cn("mx-1.5 my-1.5 flex h-[64px] flex-col items-center justify-center gap-1.5 rounded-lg text-[11px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground", isOn ? "bg-surface-selected text-foreground" : "text-secondary hover:text-foreground")}>
                <Icon className="size-5" strokeWidth={1.75} />
                <span className="truncate">{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
