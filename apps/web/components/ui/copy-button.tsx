"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function CopyButton({ text, label = "Copy", size = "sm" }: { text: string; label?: string; size?: "sm" | "icon" }) {
  const [done, setDone] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1500); } catch { setDone(false); }
  };
  if (size === "icon") return <Button size="icon" variant="ghost" aria-label={label} onClick={copy}>{done ? <Check className="size-3.5" strokeWidth={2.5} /> : <Copy className="size-3.5" strokeWidth={1.75} />}</Button>;
  return <Button size="sm" variant="outline" onClick={copy}>{done ? <Check className="size-3.5" strokeWidth={2.5} /> : <Copy className="size-3.5" strokeWidth={1.75} />} {done ? "Copied" : label}</Button>;
}

export function LogBox({ text, className }: { text: string; className?: string }) {
  return (
    <div className={cn("relative rounded-md border border-border-subtle bg-background", className)}>
      <div className="absolute right-1 top-1"><CopyButton text={text} label="Copy log" size="icon" /></div>
      <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap break-words p-3 pr-10 font-mono text-xs leading-5 text-secondary">{text}</pre>
    </div>
  );
}
