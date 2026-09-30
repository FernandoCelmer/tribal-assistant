import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";
import { ACCOUNT_COOKIE, API_BASE, maybe, server, type Schemas } from "./api";

export async function accounts(): Promise<{ list: Schemas["AccountOut"][]; current: Schemas["AccountOut"] | null }> {
  const list = (await maybe(server.GET("/api/v1/accounts"))) ?? [];
  const chosen = Number((await cookies()).get(ACCOUNT_COOKIE)?.value ?? 0);
  const current = list.find((a) => a.id === chosen) ?? list.find((a) => a.enabled) ?? list[0] ?? null;
  return { list, current };
}

export async function apiVersion(): Promise<string> {
  try {
    const response = await fetch(`${API_BASE}/health`, { cache: "no-store", signal: AbortSignal.timeout(3000) });
    const body = (await response.json()) as { version?: string };
    return body.version ?? "—";
  } catch {
    return "offline";
  }
}

export const readOnly = cache(async (): Promise<boolean> => {
  const status = await maybe(server.GET("/api/v1/assistant/status"));
  return status?.playing === false;
});

export async function writableOnly(): Promise<void> {
  if (await readOnly()) redirect("/");
}
