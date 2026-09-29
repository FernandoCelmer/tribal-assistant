"use client";

import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { toast } from "@/components/ui/toast";
import { ApiError, errorText } from "@/lib/errors";

const COORDS = /^\d{1,3}\|\d{1,3}$/;
const TEMPLATES = ["A", "B", "C"].map((t) => ({ value: t, label: `Modelo ${t}` }));

export function FarmForm() {
  const router = useRouter();
  const [coords, setCoords] = useState("");
  const [template, setTemplate] = useState("A");
  const [wall, setWall] = useState("0");
  const [busy, setBusy] = useState(false);
  const valid = COORDS.test(coords.trim());

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!valid) return;
    setBusy(true);
    try {
      const response = await fetch("/api/v1/farm/targets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ coords: coords.trim(), template, wall_level: Math.max(0, Math.min(20, Number(wall) || 0)) }),
      });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new ApiError(response.status, errorText(result, response.status));
      toast(`${coords.trim()} adicionada ao farm`);
      setCoords("");
      setWall("0");
      router.refresh();
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel>
      <PanelHeader title={<><Plus className="size-4 text-secondary" strokeWidth={1.75} />Novo alvo</>} description="Bárbaras também podem ser adicionadas pela página Arredores." />
      <PanelBody>
        <form onSubmit={submit} className="grid grid-cols-2 items-end gap-3 md:grid-cols-[minmax(0,1fr)_160px_120px_auto]">
          <Field label="Coordenadas" hint="Formato x|y" className="col-span-2 md:col-span-1">
            <Input value={coords} onChange={(e) => setCoords(e.target.value)} placeholder="500|500" inputMode="numeric" pattern="\d{1,3}\|\d{1,3}" required className="font-mono" aria-invalid={coords !== "" && !valid} />
          </Field>
          <Field label="Modelo" hint="Assistente de saque">
            <Select aria-label="Modelo" value={template} onChange={setTemplate} options={TEMPLATES} />
          </Field>
          <Field label="Muralha" hint="Nível 0–20">
            <Input type="number" min={0} max={20} value={wall} onChange={(e) => setWall(e.target.value)} className="tabular-nums" />
          </Field>
          <div className="col-span-2 md:col-span-1 md:pb-5">
            <Button type="submit" loading={busy} disabled={!valid} className="h-12 w-full md:h-9 md:w-auto"><Plus className="size-4" strokeWidth={2} />Adicionar alvo</Button>
          </div>
        </form>
      </PanelBody>
    </Panel>
  );
}
