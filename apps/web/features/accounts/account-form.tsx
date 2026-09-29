"use client";

import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { toast } from "@/components/ui/toast";
import { SwitchRow } from "@/features/settings/switch";
import { ApiError, errorText } from "@/lib/errors";

const EMPTY = { world_url: "", username: "", password: "", name: "", headless: false };

export function AccountForm() {
  const router = useRouter();
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const url = form.world_url.trim();
  const urlOk = /^https?:\/\/[^\s/]+\.[^\s]+$/.test(url);
  const ready = urlOk && form.username.trim() !== "" && form.password !== "";

  const set = <K extends keyof typeof EMPTY>(key: K, value: (typeof EMPTY)[K]) => setForm((f) => ({ ...f, [key]: value }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!ready || busy) return;
    setBusy(true);
    setError(null);
    try {
      const body = { world_url: url.replace(/\/+$/, ""), username: form.username.trim(), password: form.password, name: form.name.trim() || null, headless: form.headless };
      const response = await fetch("/api/v1/accounts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new ApiError(response.status, errorText(result, response.status));
      setForm(EMPTY);
      toast(`Conta ${(result as { name?: string } | null)?.name ?? body.username} adicionada`);
      router.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel>
      <PanelHeader title={<><Plus className="size-4 text-secondary" strokeWidth={1.75} />Nova conta</>} description="Login do Tribal Wars que o assistente vai usar." />
      <PanelBody>
        <form onSubmit={submit} className="space-y-4" autoComplete="off">
          <Field label="Endereço do mundo" hint={url && !urlOk ? "Use o endereço completo, com https://." : "Ex.: https://br145.tribalwars.com.br"}>
            <Input value={form.world_url} onChange={(e) => set("world_url", e.target.value)} placeholder="https://br145.tribalwars.com.br" inputMode="url" required className="h-11 font-mono md:h-9" />
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Usuário">
              <Input value={form.username} onChange={(e) => set("username", e.target.value)} required autoComplete="off" className="h-11 md:h-9" />
            </Field>
            <Field label="Senha" hint="Guardada criptografada no banco.">
              <Input type="password" value={form.password} onChange={(e) => set("password", e.target.value)} required autoComplete="new-password" className="h-11 md:h-9" />
            </Field>
          </div>
          <Field label="Nome no painel" hint="Opcional. Padrão: usuário e mundo.">
            <Input value={form.name} onChange={(e) => set("name", e.target.value)} maxLength={80} className="h-11 md:h-9" />
          </Field>
          <div className="rounded-md border border-border-subtle px-3 py-3">
            <SwitchRow title="Navegador sem janela" text="Roda escondido. Login com captcha precisa de janela." checked={form.headless} onChange={(v) => set("headless", v)} />
          </div>
          {error && <p role="alert" className="rounded-md border border-status-bad/30 bg-status-bad/10 px-3 py-2 text-[13px] text-status-bad">{error}</p>}
          <div className="flex justify-end">
            <Button type="submit" loading={busy} disabled={!ready} className="h-11 w-full md:h-9 md:w-auto"><Plus className="size-4" strokeWidth={1.75} />Adicionar conta</Button>
          </div>
        </form>
      </PanelBody>
    </Panel>
  );
}
