import { PageHeader } from "@/components/layout/page";
import { LogsView } from "@/features/logs";
import { maybe, server } from "@/lib/api";

const LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"];

export default async function LogsPage({ searchParams }: { searchParams: Promise<{ level?: string; q?: string }> }) {
  const params = await searchParams;
  const level = params.level && LEVELS.includes(params.level) ? params.level : "INFO";
  const q = params.q?.trim() ?? "";

  const rows = await maybe(server.GET("/api/v1/logs", { params: { query: { level, limit: 150, q: q || undefined } } }));

  return (
    <div className="space-y-6">
      <PageHeader title="Logs" description="O que a aplicação registrou, do mais recente ao mais antigo, com as novas linhas chegando ao vivo." shortDescription="Registro da aplicação, ao vivo." />
      <LogsView initial={rows ?? []} level={level} q={q} />
    </div>
  );
}
