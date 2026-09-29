import createClient from "openapi-fetch";
import { cookies } from "next/headers";
import type { components, paths } from "./api.d";
import { ApiError, errorText } from "./errors";

export const API_BASE = (process.env.TRIBAL_API ?? "http://127.0.0.1:8000").replace(/\/$/, "");
export const ACCOUNT_COOKIE = "tw_account";

export type Schemas = components["schemas"];

export { ApiError, errorText } from "./errors";

async function account(): Promise<string | null> {
  try {
    return (await cookies()).get(ACCOUNT_COOKIE)?.value ?? null;
  } catch {
    return null;
  }
}

export const server = createClient<paths>({
  baseUrl: API_BASE,
  cache: "no-store",
  fetch: async (input) => {
    const request = new Request(input);
    const id = await account();
    if (id) request.headers.set("x-account", id);
    return fetch(request, { signal: AbortSignal.timeout(30_000) });
  },
});

export async function data<T>(call: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  const { data: body, error, response } = await call;
  if (error !== undefined || body === undefined) throw new ApiError(response.status, errorText(error, response.status));
  return body;
}

export async function maybe<T>(call: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T | null> {
  try {
    return await data(call);
  } catch {
    return null;
  }
}
