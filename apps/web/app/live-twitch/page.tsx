import { TwitchScreen } from "@/features/twitch/screen";

export const metadata = { title: "Ao vivo na Twitch", description: "Tela de transmissão do Tribal Assistant: jogo, aldeia, decisões dos agentes e atividade em tempo real." };

export default async function LiveTwitchPage({ searchParams }: { searchParams: Promise<{ village?: string; since?: string; bg?: string }> }) {
  const { village, since, bg } = await searchParams;
  const only = village && /^\d+$/.test(village) ? Number(village) : null;
  return <TwitchScreen only={only} since={since ?? null} transparent={bg === "transparent"} />;
}
