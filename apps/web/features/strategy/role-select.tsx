"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useReadOnly } from "@/components/layout/read-only";
import { Select } from "@/components/ui/select";
import { toast } from "@/components/ui/toast";
import { errorText } from "@/lib/errors";
import { ROLES } from "@/lib/game";

const CHOICES = ["growth", "defense", "offensive", "support", "expansion"] as const;

export function RoleSelect({ villageId, role, manual }: { villageId: number; role: string; manual: boolean }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const locked = useReadOnly();
  const [value, setValue] = useState(manual ? role : "");

  const change = async (next: string) => {
    const previous = value;
    setValue(next);
    setBusy(true);
    try {
      const response = await fetch(`/api/v1/agents/villages/${villageId}/role`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: next || null, reason: next ? "escolhido no painel" : "" }),
      });
      if (!response.ok) throw new Error(errorText(await response.json().catch(() => null), response.status));
      toast(next ? `Papel fixado: ${ROLES[next] ?? next}` : "Papel volta a ser automático");
      router.refresh();
    } catch (err) {
      setValue(previous);
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
    }
  };

  if (locked) return null;

  return (
    <Select
      aria-label="Papel da aldeia"
      value={value}
      disabled={busy}
      onChange={change}
      options={[
        { value: "", label: "Automático", hint: manual ? undefined : ROLES[role] ?? role },
        ...CHOICES.map((r) => ({ value: r, label: ROLES[r] })),
      ]}
      className="w-full sm:w-56"
    />
  );
}
