import type { MetadataRoute } from "next";

const SITE = process.env.SITE_URL ?? "https://tw.fernandocelmer.com";
const PAGES = ["", "/live", "/village", "/strategy", "/agents", "/charts", "/challenges", "/reports", "/nearby", "/parameters"];

export default function sitemap(): MetadataRoute.Sitemap {
  return PAGES.map((path) => ({ url: `${SITE}${path}`, changeFrequency: path === "/live" ? "always" : "hourly", priority: path === "" ? 1 : path === "/live" ? 0.9 : 0.6 }));
}
