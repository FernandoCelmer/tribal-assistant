import { Bot, Castle, ChartLine, Compass, KeyRound, LayoutDashboard, Map, ScrollText, Settings, Swords, TextSearch, Workflow } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type NavItem = { href: string; label: string; icon: LucideIcon; exact?: boolean };
export type NavGroup = { label: string; items: NavItem[] };

export const NAV: NavGroup[] = [
  {
    label: "Jogo",
    items: [
      { href: "/", label: "Visão geral", icon: LayoutDashboard, exact: true },
      { href: "/aldeia", label: "Aldeia", icon: Castle },
      { href: "/arredores", label: "Arredores", icon: Map },
      { href: "/relatorios", label: "Relatórios", icon: ScrollText },
      { href: "/farm", label: "Farm", icon: Swords },
    ],
  },
  {
    label: "Agentes",
    items: [
      { href: "/estrategia", label: "Estratégia", icon: Compass },
      { href: "/agentes", label: "Agentes", icon: Bot },
      { href: "/graficos", label: "Gráficos", icon: ChartLine },
      { href: "/grafos", label: "Grafos", icon: Workflow },
      { href: "/logs", label: "Logs", icon: TextSearch },
    ],
  },
  {
    label: "Sistema",
    items: [
      { href: "/contas", label: "Contas", icon: KeyRound },
      { href: "/configuracoes", label: "Configurações", icon: Settings },
    ],
  },
];

export const MOBILE: NavItem[] = [
  { href: "/", label: "Início", icon: LayoutDashboard, exact: true },
  { href: "/aldeia", label: "Aldeia", icon: Castle },
  { href: "/estrategia", label: "Estratégia", icon: Compass },
  { href: "/agentes", label: "Agentes", icon: Bot },
  { href: "/configuracoes", label: "Ajustes", icon: Settings },
];

export function active(pathname: string, item: NavItem): boolean {
  return item.exact ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`);
}
