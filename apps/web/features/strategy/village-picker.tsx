"use client";

import { Castle } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Select } from "@/components/ui/select";

export function VillagePicker({ villages, value }: { villages: { id: number; name: string }[]; value: number }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  if (villages.length < 2) return null;

  return (
    <Select
      aria-label="Aldeia"
      value={String(value)}
      icon={<Castle className="size-4" strokeWidth={1.75} />}
      options={villages.map((v) => ({ value: String(v.id), label: v.name || `Aldeia ${v.id}` }))}
      onChange={(v) => {
        const q = new URLSearchParams(params.toString());
        q.set("village", v);
        router.replace(`${pathname}?${q.toString()}`, { scroll: false });
      }}
      className="w-full md:w-64"
    />
  );
}
