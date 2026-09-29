import { PageSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <PageSkeleton title="Logs" description="O que a aplicação registrou, do mais recente ao mais antigo, com as novas linhas chegando ao vivo." variant="table" label="Carregando logs" />;
}
