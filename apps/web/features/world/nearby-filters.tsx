"use client";

import { Radar } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { SegmentedControl } from "@/components/ui/segmented";
import { Select } from "@/components/ui/select";
import { VillagePicker, type VillageChoice } from "@/features/village";
import { KINDS, RADII, type Kind } from "./options";

export function NearbyFilters({ villages, village, kind, radius }: { villages: VillageChoice[]; village: number | null; kind: Kind; radius: number }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const set = (key: string, value: string) => {
    const query = new URLSearchParams(params.toString());
    query.set(key, value);
    router.replace(`${pathname}?${query.toString()}`, { scroll: false });
  };

  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-center">
      <SegmentedControl label="Tipo de aldeia" value={kind} options={KINDS} onChange={(v) => set("kind", v)} className="md:w-[360px]" />
      <div className="flex gap-3">
        <Select
          aria-label="Raio"
          size="lg"
          value={String(radius)}
          onChange={(v) => set("radius", v)}
          icon={<Radar className="size-4" strokeWidth={1.75} />}
          options={RADII.map((r) => ({ value: String(r), label: `Raio ${r}` }))}
          className="h-[42px] w-full md:w-36"
        />
        <VillagePicker villages={villages} current={village} className="h-[42px] md:w-56" />
      </div>
    </div>
  );
}
