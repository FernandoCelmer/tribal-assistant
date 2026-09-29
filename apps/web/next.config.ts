import type { NextConfig } from "next";
import { version } from "./package.json";

const config: NextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  output: "standalone",
  env: { WEB_VERSION: version },
  images: { remotePatterns: [{ protocol: "https", hostname: "dsbr.innogamescdn.com" }] },
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
