import { LiveFlow } from "@/features/live";

export const metadata = { title: "Ao vivo · Tribal Assistant" };

export default async function LivePage({ searchParams }: { searchParams: Promise<{ village?: string; bg?: string; edit?: string; layout?: string }> }) {
  const { village, bg, edit, layout } = await searchParams;
  const only = village && /^\d+$/.test(village) ? Number(village) : null;
  return <LiveFlow only={only} transparent={bg === "transparent"} edit={edit === "1"} saved={layout ?? null} />;
}
