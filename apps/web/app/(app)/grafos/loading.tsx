import { PageSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <PageSkeleton title="Grafos" description="Como cada agente decide: de quem partiu a chamada, qual ferramenta usou e o que aconteceu no jogo." label="Carregando grafo" />;
}
