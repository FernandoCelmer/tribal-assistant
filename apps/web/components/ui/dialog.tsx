"use client";

import { createPortal } from "react-dom";
import { Loader2, X } from "lucide-react";
import { type ReactNode, useEffect, useId, useRef, useState } from "react";
import { Button } from "./button";
import { Field, Input } from "./input";
import { cn } from "@/lib/utils";

export function Dialog({
  open,
  onClose,
  title,
  description,
  icon,
  children,
  footer,
  className,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  className?: string;
}) {
  const id = useId();
  const descriptionId = useId();
  const box = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  close.current = onClose;

  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusable = () =>
      Array.from(
        box.current?.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ) ?? [],
      );
    const wanted = box.current?.querySelector<HTMLElement>("[autofocus]");
    const first = focusable().find(
      (el) => el.getAttribute("aria-label") !== "Close modal",
    );
    (wanted ?? first ?? box.current)?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        close.current();
        return;
      }
      if (e.key !== "Tab" || !box.current) return;
      const items = focusable();
      if (items.length === 0) {
        e.preventDefault();
        box.current.focus();
        return;
      }
      const head = items[0];
      const tail = items[items.length - 1];
      const active = document.activeElement;
      if (e.shiftKey && (active === head || !box.current.contains(active))) {
        e.preventDefault();
        tail.focus();
      } else if (!e.shiftKey && active === tail) {
        e.preventDefault();
        head.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
      opener?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-background/80 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={box}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={id}
        aria-describedby={description ? descriptionId : undefined}
        className={cn("flex max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-md flex-col rounded-[14px] border border-border bg-surface focus:outline-none sm:w-full sm:rounded-lg", className)}
      >
        <div className="flex shrink-0 items-start justify-between gap-3 px-6 pt-5 sm:px-4 sm:pt-4">
          <div className="flex min-w-0 items-start gap-3">
            {icon}
            <div className="min-w-0 pt-2 sm:pt-0">
              <h2 id={id} className="text-base font-semibold leading-6">
                {title}
              </h2>
              {description && (
                <div id={descriptionId} className="mt-1 text-sm text-secondary">
                  {description}
                </div>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="-mr-3 -mt-2 flex size-11 shrink-0 items-center justify-center rounded-md text-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground sm:-mr-1 sm:-mt-1 sm:size-8"
            aria-label="Close modal"
          >
            <X className="size-4" />
          </button>
        </div>
        {children && (
          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5 sm:px-4 sm:py-4">
            {children}
          </div>
        )}
        {footer && (
          <div className="grid shrink-0 grid-cols-1 gap-2 border-t border-border px-6 py-4 min-[350px]:grid-cols-2 sm:flex sm:flex-wrap sm:justify-end sm:px-4 sm:py-3">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  icon,
  confirmLabel = "Confirm",
  confirmIcon,
  cancelLabel = "Cancel",
  pending,
  danger,
  disabled,
  className,
  children,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description?: ReactNode;
  icon?: ReactNode;
  confirmLabel?: string;
  confirmIcon?: ReactNode;
  cancelLabel?: string;
  pending?: boolean;
  danger?: boolean;
  disabled?: boolean;
  className?: string;
  children?: ReactNode;
}) {
  const formId = useId();
  const [fired, setFired] = useState(false);
  useEffect(() => {
    if (!open) setFired(false);
  }, [open]);
  const busy = !!pending || fired;
  const blocked = busy || !!disabled;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      icon={icon}
      className={className}
      footer={
        <>
          <Button
            variant="outline"
            className="min-h-12 w-full sm:h-9 sm:min-h-0 sm:w-auto sm:border-0 sm:bg-transparent sm:text-secondary sm:hover:bg-surface-hover sm:hover:text-foreground"
            onClick={onClose}
            disabled={busy}
          >
            {cancelLabel}
          </Button>
          <Button
            type="submit"
            form={formId}
            variant={
              danger ? (confirmIcon ? "danger" : "destructive") : "default"
            }
            className="min-h-12 w-full sm:h-9 sm:min-h-0 sm:w-auto"
            disabled={blocked}
            aria-busy={busy || undefined}
          >
            {busy ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              confirmIcon
            )}
            {busy ? "Working…" : confirmLabel}
          </Button>
        </>
      }
    >
      <form
        id={formId}
        onSubmit={(e) => {
          e.preventDefault();
          if (blocked) return;
          setFired(true);
          onConfirm();
        }}
      >
        {children}
      </form>
    </Dialog>
  );
}

export function PromptDialog({
  open,
  onClose,
  onSubmit,
  title,
  description,
  label,
  hint,
  placeholder,
  type = "text",
  submitLabel = "Save",
  pending,
  error,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (value: string) => void;
  title: string;
  description?: ReactNode;
  label: string;
  hint?: string;
  placeholder?: string;
  type?: string;
  submitLabel?: string;
  pending?: boolean;
  error?: string | null;
}) {
  const [value, setValue] = useState("");
  useEffect(() => {
    if (open) setValue("");
  }, [open]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={pending}>
            Cancel
          </Button>
          <Button
            onClick={() => onSubmit(value)}
            disabled={pending || !value.trim()}
          >
            {pending ? "Working…" : submitLabel}
          </Button>
        </>
      }
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim()) onSubmit(value);
        }}
      >
        <Field label={label} hint={hint}>
          <Input
            type={type}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={placeholder}
            className="font-mono"
            autoFocus
          />
        </Field>
        {error && (
          <div className="mt-3 text-sm text-foreground border border-foreground rounded-md px-3 py-2">
            {error}
          </div>
        )}
      </form>
    </Dialog>
  );
}
