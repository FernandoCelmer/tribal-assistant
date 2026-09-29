import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
      <h1 className="text-[26px] font-semibold">Página não encontrada</h1>
      <Link href="/" className="text-sm text-secondary hover:text-foreground">Voltar para a visão geral</Link>
    </div>
  );
}
