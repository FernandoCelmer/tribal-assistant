import { Clock, Gauge, Hand, SlidersHorizontal } from "lucide-react";
import { PageHeader } from "@/components/layout/page";
import { AutoRefresh } from "@/components/ui/auto-refresh";
import { Stat } from "@/components/ui/stat";
import { KnobsTable, knobLabel } from "@/features/knobs";
import { maybe, server } from "@/lib/api";
import { num, relative } from "@/lib/format";

export default async function KnobsPage() {
  const items = (await maybe(server.GET("/api/v1/knobs"))) ?? [];
  const tuning = items.filter((k) => k.self_tuning).length;
  const moved = items.filter((k) => Math.abs(k.value - k.default) > 1e-9).length;
  const manual = items.filter((k) => k.reason === "ajuste manual").length;
  const latest = items.filter((k) => k.updated_at).toSorted((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""))[0];

  return (
    <div className="space-y-6">
      <PageHeader title="Parâmetros" description="Os números que decidem quanto os agentes guardam, esperam e mandam. Os autoajustáveis mudam sozinhos a cada hora conforme as últimas 6 horas de rodadas." shortDescription="Parâmetros dos agentes." />

      <div className="flex justify-end"><AutoRefresh every={60_000} /></div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Parâmetros" value={num(items.length)} icon={SlidersHorizontal} hint={`${num(tuning)} se ajustam sozinhos`} />
        <Stat label="Fora do padrão" value={num(moved)} icon={Gauge} tone={moved ? "warn" : undefined} hint={moved ? "valor atual diferente do padrão" : "todos no padrão"} />
        <Stat label="Manuais" value={num(manual)} icon={Hand} hint="último ajuste feito por você" />
        <Stat label="Último ajuste" value={latest?.updated_at ? relative(latest.updated_at) : "—"} icon={Clock} hint={latest ? knobLabel(latest.name) : "nenhum ainda"} />
      </div>

      <KnobsTable items={items} />
    </div>
  );
}
