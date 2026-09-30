import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

const SITE = process.env.SITE_URL ?? "https://tw.fernandocelmer.com";
const DESCRIPTION =
  "Bot de Tribal Wars (Guerra Tribal) com agentes de IA que aprendem sozinhos: obras, tropas, saques, coleta, pesquisa, tribo e vida social, com painel e transmissão ao vivo de cada decisão.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: { default: "Tribal Assistant · bot de Tribal Wars com IA", template: "%s · Tribal Assistant" },
  description: DESCRIPTION,
  applicationName: "Tribal Assistant",
  keywords: ["Tribal Wars", "Guerra Tribal", "Tribal Wars bot", "bot Guerra Tribal", "Die Stämme", "agentes de IA", "farm bot", "saque", "coleta", "Twitch", "open source"],
  authors: [{ name: "Fernando Celmer", url: "https://github.com/FernandoCelmer" }],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: SITE,
    siteName: "Tribal Assistant",
    title: "Tribal Assistant · bot de Tribal Wars com IA",
    description: DESCRIPTION,
    locale: "pt_BR",
  },
  twitter: { card: "summary_large_image", title: "Tribal Assistant · bot de Tribal Wars com IA", description: DESCRIPTION },
  robots: { index: true, follow: true },
};
export const dynamic = "force-dynamic";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
