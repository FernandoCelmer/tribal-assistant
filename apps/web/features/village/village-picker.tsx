"use client";

import { Castle } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/utils";

export type VillageChoice = { id: number; name: string; coords: string };

export function VillagePicker({ villages, current, className }: { villages: VillageChoice[]; current: number | null; className?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  if (villages.length < 2) return null;

  const change = (value: string) => {
    const query = new URLSearchParams(params.toString());
    query.set("village", value);
    router.push(`${pathname}?${query.toString()}`, { scroll: false });
  };

  return (
    <Select
      aria-label="Escolher aldeia"
      value={current == null ? "" : String(current)}
      onChange={change}
      icon={<Castle className="size-4" strokeWidth={1.75} />}
      options={villages.map((v) => ({ value: String(v.id), label: v.name, hint: v.coords }))}
      className={cn("w-full md:w-64", className)}
    />
  );
}
