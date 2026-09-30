export const CDN = "https://dsbr.innogamescdn.com/asset/e94cf8a0/graphic";

export const RESOURCES = {
  wood: { label: "Madeira", icon: `${CDN}/holz.webp`, color: "text-wood" },
  clay: { label: "Argila", icon: `${CDN}/lehm.webp`, color: "text-clay" },
  iron: { label: "Ferro", icon: `${CDN}/eisen.webp`, color: "text-iron" },
} as const;

export type Resource = keyof typeof RESOURCES;

export const BUILDINGS: Record<string, string> = {
  main: "Edifício principal", barracks: "Quartel", stable: "Estábulo", garage: "Oficina", watchtower: "Torre de vigia",
  snob: "Academia", smith: "Ferreiro", place: "Praça de reunião", statue: "Estátua", market: "Mercado",
  wood: "Bosque", stone: "Poço de argila", iron: "Mina de ferro", farm: "Fazenda", storage: "Armazém",
  hide: "Esconderijo", wall: "Muralha", church: "Igreja",
};

export const UNITS: Record<string, string> = {
  spear: "Lanceiro", sword: "Espadachim", axe: "Bárbaro", archer: "Arqueiro", spy: "Explorador",
  light: "Cavalaria leve", marcher: "Arqueiro a cavalo", heavy: "Cavalaria pesada", ram: "Aríete",
  catapult: "Catapulta", knight: "Paladino", snob: "Nobre", militia: "Milícia",
};

export const AGENTS: Record<string, string> = {
  quartermaster: "Missões", strategist: "Estrategista", coordinator: "Coordenador", economy: "Economia",
  infrastructure: "Infraestrutura", recruitment: "Recrutamento", defense: "Defesa", attack: "Ataque",
  expansion: "Expansão", conquest: "Conquista", logistics: "Logística", intelligence: "Inteligência", steward: "Mordomo", diplomacy: "Diplomacia", free_finish: "Finalizar grátis", operator: "Operador",
  economist: "Economista", commander: "Comandante", raider: "Saqueador",
};

export const ROLES: Record<string, string> = {
  growth: "Crescimento", defense: "Defesa", offensive: "Ofensiva", support: "Apoio", expansion: "Expansão", emergency: "Emergência",
};

export function buildingIcon(name: string, level = 1): string {
  return `${CDN}/buildings/mid/${name}${level >= 20 ? 3 : level >= 10 ? 2 : 1}.webp`;
}

export function unitIcon(name: string): string {
  return `${CDN}/unit/unit_${name}.webp`;
}
