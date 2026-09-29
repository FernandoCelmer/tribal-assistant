import type { NextConfig } from "next";
import { version } from "./package.json";

const API = (process.env.TRIBAL_API ?? "http://127.0.0.1:8000").replace(/\/$/, "");

const config: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  env: { WEB_VERSION: version },
  images: { remotePatterns: [{ protocol: "https", hostname: "dsbr.innogamescdn.com" }] },
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${API}/api/v1/:path*` },
      { source: "/health", destination: `${API}/health` },
      { source: "/docs", destination: `${API}/docs` },
      { source: "/openapi.json", destination: `${API}/openapi.json` },
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
