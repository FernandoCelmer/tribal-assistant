import { Bot, Coins, Compass, Crown, Eye, Gem, Hammer, ScrollText, Shield, Swords, Terminal, Users, Workflow, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { agentLabel } from "./labels";

const ICONS: Record<string, LucideIcon> = {
  quartermaster: ScrollText,
  strategist: Compass,
  coordinator: Workflow,
  economy: Coins,
  economist: Coins,
  infrastructure: Hammer,
  recruitment: Users,
  commander: Users,
  defense: Shield,
  attack: Swords,
  raider: Swords,
  expansion: Crown,
  intelligence: Eye,
  steward: Gem,
  operator: Terminal,
};

export function agentIcon(key: string): LucideIcon {
  return ICONS[key] ?? Bot;
}

export function AgentMark({ agent, size = "md", className }: { agent: string; size?: "sm" | "md"; className?: string }) {
  const Icon = agentIcon(agent);
  return (
    <span
      aria-hidden
      title={agentLabel(agent)}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-md border border-border-subtle bg-background text-secondary",
        size === "sm" ? "size-6" : "size-8",
        className,
      )}
    >
      <Icon className={size === "sm" ? "size-3.5" : "size-4"} strokeWidth={1.75} />
    </span>
  );
}
