import { PageSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <PageSkeleton title="Agentes" description="Cada especialista observa uma parte da aldeia; o coordenador decide o que roda." variant="cards" label="Carregando agentes" />;
}
