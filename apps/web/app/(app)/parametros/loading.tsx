import { PageSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <PageSkeleton title="Parâmetros" description="Os números que decidem quanto os agentes guardam, esperam e mandam, e como eles se ajustam sozinhos." variant="table" label="Carregando parâmetros" />;
}
