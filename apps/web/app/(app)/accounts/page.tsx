import { PageHeader } from "@/components/layout/page";
import { AccountForm, AccountList, RuleNote } from "@/features/accounts";
import { accounts } from "@/lib/session";

export const dynamic = "force-dynamic";

export default async function AccountsPage() {
  const { list, current } = await accounts();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Contas"
        description="As contas do Tribal Wars que o assistente joga. Pause uma conta para ela parar de agir sem perder os dados."
        shortDescription="Contas que o assistente joga."
      />

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(360px,2fr)]">
        <div className="space-y-4">
          <AccountList accounts={list} current={current?.id ?? null} />
          <RuleNote />
        </div>
        <AccountForm />
      </div>
    </div>
  );
}
