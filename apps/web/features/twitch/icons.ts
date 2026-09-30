import {
  BookOpen,
  Castle,
  Coins,
  Compass,
  Crown,
  Eye,
  FlaskConical,
  Flag,
  Hammer,
  Handshake,
  Home,
  Landmark,
  Mail,
  MessagesSquare,
  Package,
  Pickaxe,
  Shield,
  ShoppingCart,
  Store,
  Swords,
  Trees,
  Trophy,
  Truck,
  UserPlus,
  Users,
  Warehouse,
  Wheat,
  type LucideIcon,
} from "lucide-react";

export const AGENT_ICONS: Record<string, LucideIcon> = {
  defense: Shield,
  economy: Coins,
  infrastructure: Landmark,
  recruitment: Users,
  attack: Swords,
  expansion: Flag,
  conquest: Trophy,
  logistics: ShoppingCart,
  intelligence: Eye,
  steward: Crown,
  diplomacy: Handshake,
  social: MessagesSquare,
};

const BUILDING_ICONS: Record<string, LucideIcon> = {
  wood: Trees,
  stone: Pickaxe,
  iron: Pickaxe,
  main: Landmark,
  barracks: Swords,
  stable: Swords,
  garage: Hammer,
  smith: Hammer,
  storage: Warehouse,
  farm: Wheat,
  wall: Castle,
  hide: Home,
  market: Store,
  statue: Crown,
  snob: Crown,
  watchtower: Eye,
  place: Flag,
};

const ACTION_ICONS: Record<string, LucideIcon> = {
  recruit_units: Users,
  send_scavenge: Pickaxe,
  unlock_scavenge: Pickaxe,
  send_farm_attack: Swords,
  send_farm_template: Swords,
  set_farm_templates: Swords,
  send_spy: Eye,
  research_unit: FlaskConical,
  use_item: BookOpen,
  create_market_offer: Store,
  accept_market_offer: Store,
  send_resources: Truck,
  send_mail: Mail,
  reply_mail: Mail,
  add_friend: UserPlus,
  accept_friend: UserPlus,
  apply_to_tribe: Handshake,
  browse_game: Compass,
  craft_event_item: Package,
};

export function actionIcon(action: string, building?: string): LucideIcon {
  if (action === "upgrade_building" && building) return BUILDING_ICONS[building] ?? Landmark;
  return ACTION_ICONS[action] ?? Package;
}

export function agentIcon(key: string): LucideIcon {
  return AGENT_ICONS[key] ?? Users;
}
