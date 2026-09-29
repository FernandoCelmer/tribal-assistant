"use client";

import { type ReactNode, useEffect, useId, useRef, useState } from "react";
import { Button } from "./button";
import { Dialog } from "./dialog";
import { Field, Input } from "./input";

export type ConfirmOptions = {
  title: string;
  description?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "default" | "danger";
};

export type PromptOptions = {
  title: string;
  description?: ReactNode;
  label: string;
  placeholder?: string;
  defaultValue?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  type?: string;
  required?: boolean;
};

type Request =
  | { id: number; kind: "confirm"; options: ConfirmOptions; resolve: (value: boolean) => void }
  | { id: number; kind: "prompt"; options: PromptOptions; resolve: (value: string | null) => void };

const EVENT = "tribal-dialog";
let hosts = 0;
let sequence = 0;

export function confirmDialog(options: ConfirmOptions | string): Promise<boolean> {
  const opts = typeof options === "string" ? { title: options } : options;
  if (hosts === 0) return Promise.resolve(false);
  return new Promise((resolve) => window.dispatchEvent(new CustomEvent<Request>(EVENT, { detail: { id: ++sequence, kind: "confirm", options: opts, resolve } })));
}

export function promptDialog(options: PromptOptions): Promise<string | null> {
  if (hosts === 0) return Promise.resolve(null);
  return new Promise((resolve) => window.dispatchEvent(new CustomEvent<Request>(EVENT, { detail: { id: ++sequence, kind: "prompt", options, resolve } })));
}

export function DialogHost() {
  const [queue, setQueue] = useState<Request[]>([]);

  useEffect(() => {
    hosts += 1;
    const add = (e: Event) => setQueue((list) => [...list, (e as CustomEvent<Request>).detail]);
    window.addEventListener(EVENT, add);
    return () => {
      hosts -= 1;
      window.removeEventListener(EVENT, add);
    };
  }, []);

  const current = queue[0];
  if (!current) return null;
  const done = () => setQueue((list) => list.filter((r) => r.id !== current.id));

  return current.kind === "confirm"
    ? <ConfirmRequest key={current.id} options={current.options} settle={(value) => { current.resolve(value); done(); }} />
    : <PromptRequest key={current.id} options={current.options} settle={(value) => { current.resolve(value); done(); }} />;
}

const cancelClass = "min-h-12 w-full sm:h-9 sm:min-h-0 sm:w-auto sm:border-0 sm:bg-transparent sm:text-secondary sm:hover:bg-surface-hover sm:hover:text-foreground";
const confirmClass = "min-h-12 w-full sm:h-9 sm:min-h-0 sm:w-auto";

function useOnce<T>(settle: (value: T) => void) {
  const fired = useRef(false);
  return (value: T) => {
    if (fired.current) return;
    fired.current = true;
    settle(value);
  };
}

function ConfirmRequest({ options, settle }: { options: ConfirmOptions; settle: (value: boolean) => void }) {
  const { title, description, confirmLabel = "Confirmar", cancelLabel = "Cancelar", tone = "default" } = options;
  const finish = useOnce(settle);

  return (
    <Dialog
      open
      sheet
      onClose={() => finish(false)}
      title={title}
      description={description}
      footer={
        <>
          <Button variant="outline" className={cancelClass} onClick={() => finish(false)}>{cancelLabel}</Button>
          <Button variant={tone === "danger" ? "danger" : "default"} className={confirmClass} data-autofocus onClick={() => finish(true)}>{confirmLabel}</Button>
        </>
      }
    />
  );
}

function PromptRequest({ options, settle }: { options: PromptOptions; settle: (value: string | null) => void }) {
  const { title, description, label, placeholder, defaultValue = "", confirmLabel = "Confirmar", cancelLabel = "Cancelar", type = "text", required = true } = options;
  const formId = useId();
  const [value, setValue] = useState(defaultValue);
  const finish = useOnce(settle);
  const blocked = required && !value.trim();

  return (
    <Dialog
      open
      sheet
      onClose={() => finish(null)}
      title={title}
      description={description}
      footer={
        <>
          <Button variant="outline" className={cancelClass} onClick={() => finish(null)}>{cancelLabel}</Button>
          <Button type="submit" form={formId} className={confirmClass} disabled={blocked}>{confirmLabel}</Button>
        </>
      }
    >
      <form
        id={formId}
        onSubmit={(e) => {
          e.preventDefault();
          if (!blocked) finish(value);
        }}
      >
        <Field label={label}>
          <Input type={type} value={value} onChange={(e) => setValue(e.target.value)} placeholder={placeholder} data-autofocus onFocus={(e) => e.currentTarget.select()} />
        </Field>
      </form>
    </Dialog>
  );
}
