import { PageSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <PageSkeleton title="Desafios" description="As conquistas do jogo, o progresso de cada uma e qual agente persegue ou por que fica de fora." variant="table" label="Carregando desafios" />;
}
