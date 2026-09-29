"use client";

import { History, Pencil, SlidersHorizontal } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ActionButton } from "@/components/ui/action-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Cell, DataTable } from "@/components/ui/data-table";
import { Dialog } from "@/components/ui/dialog";
import { promptDialog } from "@/components/ui/dialog-host";
import { toast } from "@/components/ui/toast";
import type { Schemas } from "@/lib/api";
import { ApiError, errorText } from "@/lib/errors";
import { relative, short } from "@/lib/format";
import { cn } from "@/lib/utils";

type Knob = Schemas["KnobOut"];
type Tuned = Schemas["KnobTuneOut"];

const LABELS: Record<string, string> = {
  base_stock_share: "Reserva mínima do estoque",
  filler_wait_hours: "Espera antes de obra encaixe",
  scavenge_share: "Lanceiros na coleta",
};

export function knobLabel(name: string): string {
  if (LABELS[name]) return LABELS[name];
  const text = name.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

const DECIMAL = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });

export function knobValue(knob: Pick<Knob, "name" | "share" | "integer">, value: number | null | undefined): string {
  if (value == null) return "—";
  if (knob.share) return `${DECIMAL.format(value * 100)}%`;
  if (knob.integer) return DECIMAL.format(Math.round(value));
  if (knob.name.endsWith("_hours")) return `${DECIMAL.format(value)} h`;
  if (knob.name.endsWith("_minutes")) return `${DECIMAL.format(value)} min`;
  return DECIMAL.format(value);
}

function changed(knob: Knob): boolean {
  return Math.abs(knob.value - knob.default) > 1e-9;
}

export function TuneButton() {
  return (
    <ActionButton
      path="/api/v1/knobs/tune"
      variant="outline"
      size="sm"
      confirm={{ title: "Ajustar os parâmetros agora?", description: "Mede as últimas 6 horas de rodadas e move cada parâmetro autoajustável um passo na direção que a regra dele pede. Sem rodadas suficientes nada muda.", confirmLabel: "Ajustar agora" }}
      done={(result) => {
        const changes = (result as Tuned | null)?.changes ?? [];
        return changes.length ? `${changes.length} ${changes.length === 1 ? "parâmetro ajustado" : "parâmetros ajustados"}` : "Nada a ajustar agora";
      }}
    >
      <SlidersHorizontal className="size-3.5" strokeWidth={1.75} /> Ajustar agora
    </ActionButton>
  );
}

function HistoryDialog({ knob, onClose }: { knob: Knob; onClose: () => void }) {
  const rows = knob.history.toReversed();
  return (
    <Dialog open sheet onClose={onClose} title={knobLabel(knob.name)} description={knob.description} className="sm:max-w-xl">
      {rows.length === 0 ? (
        <p className="py-6 text-center text-[13px] text-secondary">Ainda no valor padrão, nenhuma mudança registrada.</p>
      ) : (
        <ol className="max-h-[60vh] divide-y divide-border-subtle overflow-y-auto">
          {rows.map((h, i) => (
            <li key={`${h.at}-${i}`} className="py-2.5 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-[13px] tabular-nums">{knobValue(knob, h.from)} → <span className="font-semibold">{knobValue(knob, h.to)}</span></span>
                <span className="shrink-0 text-[12px] text-muted-foreground">{short(h.at)}</span>
              </div>
              <div className="mt-0.5 text-[13px] text-secondary">{h.why || "—"}</div>
            </li>
          ))}
        </ol>
      )}
    </Dialog>
  );
}

export function KnobsTable({ items }: { items: Knob[] }) {
  const router = useRouter();
  const [open, setOpen] = useState<Knob | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const edit = async (knob: Knob) => {
    const raw = await promptDialog({
      title: `Ajustar ${knobLabel(knob.name)}`,
      description: `${knob.description}. Padrão: ${knobValue(knob, knob.default)}.${knob.share ? " Informe uma fração entre 0 e 1 (0,25 = 25%)." : ""}${knob.self_tuning ? " O autoajuste pode mudar o valor de novo nas próximas horas." : ""}`,
      label: "Novo valor",
      type: "text",
      defaultValue: String(knob.value).replace(".", ","),
      confirmLabel: "Salvar",
    });
    if (raw == null) return;
    const value = Number(raw.trim().replace(",", "."));
    if (!Number.isFinite(value) || value <= 0) return toast("Informe um número maior que zero", "error");
    if (knob.share && value > 1) return toast("Fração precisa ficar entre 0 e 1", "error");
    setBusy(knob.name);
    try {
      const response = await fetch(`/api/v1/knobs/${encodeURIComponent(knob.name)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ value }) });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new ApiError(response.status, errorText(result, response.status));
      toast(`${knobLabel(knob.name)}: ${knobValue(knob, (result as Knob).value)}`);
      router.refresh();
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <DataTable
        title="Parâmetros"
        rows={items}
        rowKey={(k) => k.name}
        noun={["parâmetro", "parâmetros"]}
        action={<TuneButton />}
        empty={{ icon: SlidersHorizontal, title: "Nenhum parâmetro", text: "Os parâmetros aparecem quando a API responde." }}
        minWidth={1020}
        rowClassName={(k) => (changed(k) ? "bg-surface-hover/40" : undefined)}
        columns={[
          {
            key: "name",
            label: "Parâmetro",
            width: 32,
            render: (k) => (
              <span className="block min-w-0">
                <Cell className="font-medium" title={k.name}>{knobLabel(k.name)}</Cell>
                <Cell muted className="text-[12px]" title={k.description}>{k.description}</Cell>
              </span>
            ),
          },
          {
            key: "value",
            label: "Valor",
            width: 16,
            render: (k) => (
              <span className="flex min-w-0 items-baseline gap-2 whitespace-nowrap">
                <span className={cn("font-mono text-[13px] tabular-nums", changed(k) && "font-semibold text-gold")}>{knobValue(k, k.value)}</span>
                {changed(k) ? <span className="truncate text-[12px] text-muted-foreground">padrão {knobValue(k, k.default)}</span> : <span className="text-[12px] text-muted-foreground">padrão</span>}
              </span>
            ),
          },
          { key: "auto", label: "Autoajuste", width: 10, render: (k) => <Badge tone={k.self_tuning ? "success" : "neutral"}>{k.self_tuning ? "sim" : "não"}</Badge> },
          {
            key: "reason",
            label: "Último ajuste",
            width: 30,
            hide: "md",
            render: (k) => (
              <span className="block min-w-0">
                <Cell className="text-[13px]" muted={!k.reason} title={k.reason}>{k.reason || "nunca ajustado"}</Cell>
                <Cell muted className="text-[12px]" title={k.updated_at ?? undefined}>{k.updated_at ? relative(k.updated_at) : "—"}</Cell>
              </span>
            ),
          },
          {
            key: "actions",
            label: "",
            width: 12,
            align: "right",
            render: (k) => (
              <span className="inline-flex items-center gap-1">
                <Button size="icon" variant="ghost" aria-label={`Histórico de ${knobLabel(k.name)}`} title="Histórico" onClick={() => setOpen(k)}>
                  <History className="size-4" strokeWidth={1.75} />
                  {k.history.length > 0 && <span className="sr-only">{k.history.length} mudanças</span>}
                </Button>
                <Button size="icon" variant="ghost" aria-label={`Editar ${knobLabel(k.name)}`} title="Editar valor" loading={busy === k.name} onClick={() => edit(k)}>
                  {busy !== k.name && <Pencil className="size-4" strokeWidth={1.75} />}
                </Button>
              </span>
            ),
          },
        ]}
      />
      {open && <HistoryDialog knob={open} onClose={() => setOpen(null)} />}
    </>
  );
}
