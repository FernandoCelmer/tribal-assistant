import type { MetadataRoute } from "next";

const SITE = process.env.SITE_URL ?? "https://tw.fernandocelmer.com";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/", "/docs", "/openapi.json"] },
    sitemap: `${SITE}/sitemap.xml`,
    host: SITE,
  };
}
