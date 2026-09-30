import { Bot, Castle, ChartLine, Compass, KeyRound, LayoutDashboard, Map, ScrollText, Settings, SlidersHorizontal, TextSearch, Trophy } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type NavItem = { href: string; label: string; icon: LucideIcon; exact?: boolean; writes?: boolean };
export type NavGroup = { label: string; items: NavItem[] };

export const NAV: NavGroup[] = [
  {
    label: "Jogo",
    items: [
      { href: "/", label: "Visão geral", icon: LayoutDashboard, exact: true },
      { href: "/village", label: "Aldeia", icon: Castle },
      { href: "/nearby", label: "Arredores", icon: Map },
      { href: "/reports", label: "Relatórios", icon: ScrollText },
      { href: "/challenges", label: "Desafios", icon: Trophy },
    ],
  },
  {
    label: "Agentes",
    items: [
      { href: "/strategy", label: "Estratégia", icon: Compass },
      { href: "/agents", label: "Agentes", icon: Bot },
      { href: "/charts", label: "Gráficos", icon: ChartLine },
      { href: "/parameters", label: "Parâmetros", icon: SlidersHorizontal },
      { href: "/logs", label: "Logs", icon: TextSearch },
    ],
  },
  {
    label: "Sistema",
    items: [
      { href: "/accounts", label: "Contas", icon: KeyRound, writes: true },
      { href: "/settings", label: "Configurações", icon: Settings, writes: true },
    ],
  },
];

export const MOBILE: NavItem[] = [
  { href: "/", label: "Início", icon: LayoutDashboard, exact: true },
  { href: "/village", label: "Aldeia", icon: Castle },
  { href: "/strategy", label: "Estratégia", icon: Compass },
  { href: "/agents", label: "Agentes", icon: Bot },
  { href: "/settings", label: "Ajustes", icon: Settings, writes: true },
];

const MOBILE_READ_ONLY: NavItem = { href: "/charts", label: "Gráficos", icon: ChartLine };

export function navGroups(locked: boolean): NavGroup[] {
  return NAV.map((g) => ({ ...g, items: g.items.filter((i) => !(locked && i.writes)) })).filter((g) => g.items.length > 0);
}

export function mobileItems(locked: boolean): NavItem[] {
  return locked ? [...MOBILE.filter((i) => !i.writes), MOBILE_READ_ONLY] : MOBILE;
}

export function active(pathname: string, item: NavItem): boolean {
  return item.exact ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`);
}
