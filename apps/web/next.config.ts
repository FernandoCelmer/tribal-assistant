import type { NextConfig } from "next";
import { version } from "./package.json";

const config: NextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  output: "standalone",
  env: { WEB_VERSION: version },
  images: { remotePatterns: [{ protocol: "https", hostname: "dsbr.innogamescdn.com" }] },
  async redirects() {
    return [
      { source: "/aldeia/:path*", destination: "/village/:path*", permanent: true },
      { source: "/arredores/:path*", destination: "/nearby/:path*", permanent: true },
      { source: "/relatorios/:path*", destination: "/reports/:path*", permanent: true },
      { source: "/desafios/:path*", destination: "/challenges/:path*", permanent: true },
      { source: "/estrategia/:path*", destination: "/strategy/:path*", permanent: true },
      { source: "/agentes/:path*", destination: "/agents/:path*", permanent: true },
      { source: "/graficos/:path*", destination: "/charts/:path*", permanent: true },
      { source: "/grafos/:path*", destination: "/charts", permanent: true },
      { source: "/graph/:path*", destination: "/charts", permanent: true },
      { source: "/parametros/:path*", destination: "/parameters/:path*", permanent: true },
      { source: "/contas/:path*", destination: "/accounts/:path*", permanent: true },
      { source: "/configuracoes/:path*", destination: "/settings/:path*", permanent: true },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

export default config;
