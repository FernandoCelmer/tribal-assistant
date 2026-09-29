import type { ReactNode } from "react";
import "./globals.css";

export const metadata = { title: "Tribal Assistant", description: "Agentes que jogam Tribal Wars por você." };
export const dynamic = "force-dynamic";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
