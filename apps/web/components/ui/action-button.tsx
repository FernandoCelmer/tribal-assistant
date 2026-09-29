"use client";

import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Button, type ButtonProps } from "@/components/ui/button";
import { ApiError, errorText } from "@/lib/errors";
import { type ConfirmOptions, confirmDialog } from "@/components/ui/dialog-host";
import { toast } from "@/components/ui/toast";

type Props = Omit<ButtonProps, "onClick"> & {
  path: string;
  method?: "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  confirm?: string | ConfirmOptions;
  done?: (result: unknown) => string | null;
  success?: string;
  successField?: string;
  children: ReactNode;
};

export function ActionButton({ path, method = "POST", body, confirm, done, success, successField, children, ...props }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  const run = async () => {
    if (confirm && !(await confirmDialog(confirm))) return;
    setBusy(true);
    try {
      const response = await fetch(path, {
        method,
        headers: body === undefined ? undefined : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const result = response.status === 204 ? null : await response.json().catch(() => null);
      if (!response.ok) throw new ApiError(response.status, errorText(result, response.status));
      const field = successField ? (result as Record<string, unknown> | null)?.[successField] : undefined;
      const message = done?.(result) ?? (typeof field === "string" ? field : success);
      if (message) toast(message);
      router.refresh();
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
    }
  };

  return <Button {...props} loading={busy} onClick={run}>{children}</Button>;
}
