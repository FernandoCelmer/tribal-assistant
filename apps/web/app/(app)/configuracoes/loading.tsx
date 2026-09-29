import { PageSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return <PageSkeleton title="Configurações" description="Como os agentes rodam, quem usa IA e o que o servidor está usando." variant="panels" label="Carregando configurações" />;
}
