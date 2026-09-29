"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";
import { SegmentedControl } from "@/components/ui/segmented";
import { cn } from "@/lib/utils";
import { PERIODS, type Period } from "./scale";

export function useQueryNav() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [pending, start] = useTransition();

  const set = (changes: Record<string, string | null>) => {
    const q = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") q.delete(key);
      else q.set(key, value);
    }
    const query = q.toString();
    start(() => router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false }));
  };

  return { set, pending };
}

export function PeriodControl({ value, clear = [], className }: { value: Period; clear?: string[]; className?: string }) {
  const { set, pending } = useQueryNav();
  return (
    <SegmentedControl
      label="Período"
      value={value}
      options={PERIODS.map((p) => ({ id: p.id, label: p.label }))}
      onChange={(v) => set({ hours: v, ...Object.fromEntries(clear.map((k) => [k, null])) })}
      className={cn("md:h-9 md:w-60", pending && "opacity-60", className)}
    />
  );
}
