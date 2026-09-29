import { ShieldAlert } from "lucide-react";

export function RuleNote() {
  return (
    <aside className="flex gap-3 rounded-lg border border-border bg-surface px-4 py-3.5 text-[13px] text-secondary">
      <ShieldAlert className="mt-0.5 size-4 shrink-0 text-gold" strokeWidth={1.75} aria-hidden />
      <div className="space-y-1">
        <p className="font-medium text-foreground">Regra do jogo</p>
        <p>Uma pessoa só pode ter uma conta por mundo. Contas na mesma conexão não podem mandar tropas nem recursos entre si nem atacar o mesmo alvo.</p>
        <p>O assistente nunca faz ações entre as contas que gerencia: cada uma joga isolada.</p>
      </div>
    </aside>
  );
}
