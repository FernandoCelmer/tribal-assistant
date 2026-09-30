"use client";

import { Bot, Compass, Play, Sparkles, Undo2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckIndicator } from "@/components/ui/check-indicator";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { toast } from "@/components/ui/toast";
import type { Schemas } from "@/lib/api";
import { ApiError, errorText } from "@/lib/errors";
import { AGENTS, ROLES } from "@/lib/game";
import { cn } from "@/lib/utils";
import { SwitchRow } from "./switch";

type Settings = Schemas["AgentSettings"];

type Form = {
  enabled: boolean;
  dry_run: boolean;
  auto_finish_free: boolean;
  interval_minutes: string;
  llm_agents: string[];
  plan_refresh_minutes: string;
  llm_max_steps: string;
};

const LLM_AGENTS = [{ id: "strategist", text: "escreve o plano da aldeia" }];

const LIMITS = {
  interval_minutes: [1, 1440],
  plan_refresh_minutes: [5, 10080],
  llm_max_steps: [1, 20],
} as const;

function toForm(s: Settings): Form {
  return {
    enabled: s.enabled ?? false,
    dry_run: s.dry_run ?? false,
    auto_finish_free: s.auto_finish_free ?? true,
    interval_minutes: String(s.interval_minutes ?? 10),
    llm_agents: [...(s.llm_agents ?? [])].sort(),
    plan_refresh_minutes: String(s.plan_refresh_minutes ?? 360),
    llm_max_steps: String(s.llm_max_steps ?? 6),
  };
}

function toBody(f: Form) {
  return {
    enabled: f.enabled,
    dry_run: f.dry_run,
    auto_finish_free: f.auto_finish_free,
    interval_minutes: Number(f.interval_minutes),
    llm_agents: f.llm_agents,
    plan_refresh_minutes: Number(f.plan_refresh_minutes),
    llm_max_steps: Number(f.llm_max_steps),
  };
}

function invalid(f: Form): string | null {
  for (const [key, [min, max]] of Object.entries(LIMITS) as [keyof typeof LIMITS, readonly [number, number]][]) {
    const v = Number(f[key]);
    if (f[key] === "" || !Number.isInteger(v) || v < min || v > max) return key;
  }
  return null;
}

function mode(f: { enabled: boolean; dry_run: boolean }) {
  if (!f.enabled) return { label: "desligado", tone: "neutral" as const };
  return f.dry_run ? { label: "simulação", tone: "warning" as const } : { label: "ao vivo", tone: "success" as const };
}

function NumberField({ label, hint, unit, value, onChange, range, error }: { label: string; hint: string; unit?: string; value: string; onChange: (v: string) => void; range: readonly [number, number]; error: boolean }) {
  return (
    <Field label={label} hint={error ? `Use um número entre ${range[0]} e ${range[1]}.` : hint}>
      <div className="relative">
        <Input type="number" inputMode="numeric" min={range[0]} max={range[1]} value={value} onChange={(e) => onChange(e.target.value)} aria-invalid={error || undefined} className={cn("h-11 font-mono md:h-9", unit && "pr-12", error && "border-status-bad")} />
        {unit && <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-[13px] text-muted-foreground">{unit}</span>}
      </div>
    </Field>
  );
}

function Section({ title, icon, description, aside, children }: { title: string; icon: ReactNode; description?: ReactNode; aside?: ReactNode; children: ReactNode }) {
  return (
    <Panel>
      <PanelHeader title={<>{icon}{title}</>} description={description} aside={aside} />
      <PanelBody>{children}</PanelBody>
    </Panel>
  );
}

export function SettingsForm({ initial }: { initial: Settings }) {
  const router = useRouter();
  const [saved, setSaved] = useState<Form>(() => toForm(initial));
  const [form, setForm] = useState<Form>(saved);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const changed = (Object.keys(form) as (keyof Form)[]).filter((k) => JSON.stringify(form[k]) !== JSON.stringify(saved[k]));
  const dirty = changed.length > 0;
  const bad = invalid(form);
  const current = mode(saved);
  const next = mode(form);
  const icon = "size-4 text-secondary";

  const patch = <K extends keyof Form>(key: K, value: Form[K]) => setForm((f) => ({ ...f, [key]: value }));
  const toggleAgent = (id: string) => patch("llm_agents", form.llm_agents.includes(id) ? form.llm_agents.filter((a) => a !== id) : [...form.llm_agents, id].sort());

  const save = async () => {
    setBusy(true);
    try {
      const response = await fetch("/api/v1/agents/settings", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(toBody(form)) });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new ApiError(response.status, errorText(result, response.status));
      const fresh = toForm(result as Settings);
      setSaved(fresh);
      setForm(fresh);
      toast("Configurações salvas. Valem a partir da próxima rodada.");
      router.refresh();
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
      setConfirming(false);
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!dirty || bad) return;
    const goingLive = form.enabled && !form.dry_run && !(saved.enabled && !saved.dry_run);
    if (goingLive) setConfirming(true);
    else void save();
  };

  return (
    <>
      <form onSubmit={submit} noValidate className="space-y-4">
        <Section
          title="Agentes"
          icon={<Bot className={icon} strokeWidth={1.75} />}
          description="Quando e como os agentes jogam sozinhos."
          aside={<Badge tone={current.tone}>{current.label}</Badge>}
        >
          <div className="divide-y divide-border-subtle">
            <SwitchRow title="Rodar automaticamente" text="Os agentes rodam sozinhos no intervalo abaixo enquanto o servidor estiver ligado." checked={form.enabled} onChange={(v) => patch("enabled", v)} />
            <SwitchRow title="Só simular" text="Decidem e registram tudo, mas não mexem no jogo." checked={form.dry_run} onChange={(v) => patch("dry_run", v)} />
            <SwitchRow title="Concluir grátis quando possível" text="Usa o botão gratuito de concluir obras curtas. Nunca o pago." checked={form.auto_finish_free} onChange={(v) => patch("auto_finish_free", v)} />
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 border-t border-border-subtle pt-4 sm:grid-cols-2">
            <NumberField label="Intervalo entre rodadas" unit="min" hint="Menor intervalo = mais ações e mais custo de IA." value={form.interval_minutes} onChange={(v) => patch("interval_minutes", v)} range={LIMITS.interval_minutes} error={bad === "interval_minutes"} />
          </div>
        </Section>

        <Section title="Limites" icon={<Compass className={icon} strokeWidth={1.75} />} description="Decididos pelo coordenador, por papel da aldeia.">
          <div className="space-y-3 text-[13px] text-secondary">
            <p>Reserva de recursos, orçamento de recrutamento, raio e ritmo dos saques e a fila de obras mudam sozinhos com o papel de cada aldeia.</p>
            <ul className="flex flex-wrap gap-1.5">{Object.values(ROLES).map((r) => <li key={r}><Badge>{r}</Badge></li>)}</ul>
            <p>Continuam fixas: só aldeias bárbaras são atacadas, pontos premium nunca são gastos e, com ataque chegando, as tropas ficam em casa.</p>
            <Link href="/strategy" className="inline-flex items-center gap-1.5 text-foreground underline-offset-4 hover:underline"><Compass className="size-3.5" strokeWidth={1.75} />Ver valores atuais em Estratégia</Link>
          </div>
        </Section>

        <Section title="Inteligência artificial" icon={<Sparkles className={icon} strokeWidth={1.75} />} description="Só o Estrategista usa IA, para escrever o plano. Os especialistas decidem por regras, sem gastar tokens.">
          <fieldset>
            <legend className="mb-2 text-xs text-secondary">Agentes que usam IA</legend>
            <div className="space-y-2">
              {LLM_AGENTS.map((a) => {
                const on = form.llm_agents.includes(a.id);
                return (
                  <button key={a.id} type="button" role="checkbox" aria-checked={on} onClick={() => toggleAgent(a.id)} className={cn("flex min-h-12 w-full items-center gap-3 rounded-md border px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground", on ? "border-border-hover bg-surface-selected" : "border-border hover:bg-surface-hover")}>
                    <CheckIndicator selected={on} />
                    <span className="min-w-0 text-sm">{AGENTS[a.id] ?? a.id}<span className="block text-[12px] text-muted-foreground">{a.text}</span></span>
                  </button>
                );
              })}
            </div>
          </fieldset>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <NumberField label="Refazer o plano a cada" unit="min" hint="Também refaz quando o plano termina ou trava." value={form.plan_refresh_minutes} onChange={(v) => patch("plan_refresh_minutes", v)} range={LIMITS.plan_refresh_minutes} error={bad === "plan_refresh_minutes"} />
            <NumberField label="Passos por conversa" hint="Limite de chamadas de ferramenta por conversa." value={form.llm_max_steps} onChange={(v) => patch("llm_max_steps", v)} range={LIMITS.llm_max_steps} error={bad === "llm_max_steps"} />
          </div>
        </Section>

        <div className="sticky bottom-[calc(96px+env(safe-area-inset-bottom))] z-20 md:bottom-4">
          <div className={cn("flex flex-wrap items-center gap-3 rounded-lg border bg-surface/95 px-4 py-3 backdrop-blur-sm", dirty ? "border-border-hover" : "border-border")}>
            <span className="min-w-0 flex-1 text-[13px] text-secondary" aria-live="polite">
              {dirty ? `${changed.length} ${changed.length === 1 ? "alteração não salva" : "alterações não salvas"}` : "Sem alterações"}
              {dirty && next.label !== current.label && <span className="ml-2 text-foreground">· passa a {next.label}</span>}
            </span>
            <Button type="button" variant="ghost" size="sm" disabled={!dirty || busy} onClick={() => setForm(saved)}><Undo2 className="size-3.5" strokeWidth={1.75} />Desfazer</Button>
            <Button type="submit" size="sm" disabled={!dirty || !!bad} loading={busy && !confirming}>Salvar configurações</Button>
          </div>
        </div>
      </form>

      <ConfirmDialog
        open={confirming}
        onClose={() => !busy && setConfirming(false)}
        onConfirm={() => void save()}
        pending={busy}
        title="Ligar os agentes ao vivo?"
        description="No agendamento eles vão construir, recrutar, coletar e saquear sozinhos, sem simulação."
        confirmLabel="Ligar ao vivo"
        confirmIcon={<Play className="size-4" strokeWidth={1.75} aria-hidden />}
        cancelLabel="Cancelar"
      />
    </>
  );
}
