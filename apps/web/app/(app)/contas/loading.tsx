import { PageSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <PageSkeleton title="Contas" description="As contas do Tribal Wars que o assistente joga. Pause uma conta para ela parar de agir sem perder os dados." label="Carregando contas" />;
}
