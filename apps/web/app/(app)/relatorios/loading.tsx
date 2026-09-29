import { PageSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <PageSkeleton title="Relatórios" description="Resultados dos ataques, alvos e saque de cada batalha." variant="table" label="Carregando relatórios" />;
}
