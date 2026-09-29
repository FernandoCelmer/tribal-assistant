import { Settings } from "lucide-react";
import { PageHeader } from "@/components/layout/page";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel } from "@/components/ui/panel";
import { AiInfo, SettingsForm, SystemInfo } from "@/features/settings";
import { maybe, server } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const [settings, info] = await Promise.all([
    maybe(server.GET("/api/v1/agents/settings")),
    maybe(server.GET("/api/v1/system/info")),
  ]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Configurações"
        description="Como os agentes rodam, quem usa IA e o que o servidor está usando."
        shortDescription="Agentes, IA e sistema."
      />

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(320px,2fr)]">
        {settings ? <SettingsForm initial={settings} /> : (
          <Panel><EmptyState icon={Settings} title="Configurações indisponíveis" text="A API não respondeu. Confira se o servidor está no ar." /></Panel>
        )}
        <div className="space-y-4">
          {info ? (
            <>
              <AiInfo info={info.ai} />
              <SystemInfo info={info} />
            </>
          ) : (
            <Panel><EmptyState icon={Settings} title="Sistema indisponível" text="Sem resposta de /system/info." /></Panel>
          )}
        </div>
      </div>
    </div>
  );
}
