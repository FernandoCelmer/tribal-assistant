"use client";

import createClient from "openapi-fetch";
import type { paths } from "./api.d";
import { ApiError, errorText } from "./errors";

export const client = createClient<paths>({ baseUrl: "", cache: "no-store" });

export async function call<T>(request: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  const { data, error, response } = await request;
  if (error !== undefined || (data === undefined && response.status !== 204)) throw new ApiError(response.status, errorText(error, response.status));
  return data as T;
}
