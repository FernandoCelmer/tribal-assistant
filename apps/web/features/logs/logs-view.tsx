"use client";

import { ChevronDown, Pause, Play, Search, TextSearch } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Pager, usePaged } from "@/components/ui/pagination";
import { Panel } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { toast } from "@/components/ui/toast";
import { STREAM_LABEL, useEvents } from "@/features/agents/events";
import { levelTone } from "@/features/agents/live-feed";
import type { Schemas } from "@/lib/api";
import { errorText } from "@/lib/errors";
import { utc } from "@/lib/format";
import { cn } from "@/lib/utils";

type Log = Schemas["LogOut"];
type Row = Log & { live?: boolean };

export const LEVELS = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"];
export const PAGE = 150;
const KEEP = 1000;

const OPTIONS = [
  { value: "DEBUG", label: "Debug" },
  { value: "INFO", label: "Info" },
  { value: "WARNING", label: "Aviso" },
  { value: "ERROR", label: "Erro" },
];

function stamp(at: string): string {
  return utc(at).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

async function fetchLogs(level: string, q: string, before?: number): Promise<Log[]> {
  const query = new URLSearchParams({ level, limit: String(PAGE) });
  if (q) query.set("q", q);
  if (before !== undefined) query.set("before_id", String(before));
  const response = await fetch(`/api/v1/logs?${query.toString()}`, { cache: "no-store" });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(errorText(body, response.status));
  return body as Log[];
}

function syncUrl(level: string, q: string) {
  const url = new URL(window.location.href);
  url.searchParams.set("level", level);
  if (q) url.searchParams.set("q", q);
  else url.searchParams.delete("q");
  window.history.replaceState(window.history.state, "", url.toString());
}

function LogRow({ row }: { row: Row }) {
  const tone = levelTone(row.level);
  return (
    <li className={cn("grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 px-4 py-2.5 md:grid-cols-[132px_72px_minmax(0,1fr)_minmax(0,240px)] md:items-start", row.live && "select-in")}>
      <span className="font-mono text-[12px] tabular-nums text-muted-foreground md:pt-0.5" suppressHydrationWarning>{stamp(row.at)}</span>
      <span className="justify-self-end md:justify-self-start"><Badge tone={tone} className="font-mono text-[11px]">{row.level.toLowerCase()}</Badge></span>
      <span className={cn("col-span-2 whitespace-pre-wrap break-words font-mono text-[12.5px] leading-5 md:col-span-1", tone === "danger" ? "text-status-bad" : tone === "warning" ? "text-status-warn" : "text-foreground")}>{row.message}</span>
      <span className="col-span-2 truncate font-mono text-[11px] text-muted-foreground md:col-span-1 md:pt-0.5" title={`${row.source} · ${row.process}`}>
        {row.source} <span className="text-disabled">{row.process}</span>
      </span>
    </li>
  );
}

export function LogsView({ initial, level: initialLevel, q: initialQ }: { initial: Log[]; level: string; q: string }) {
  const [rows, setRows] = useState<Row[]>(initial);
  const [level, setLevel] = useState(initialLevel);
  const [q, setQ] = useState(initialQ);
  const [search, setSearch] = useState(initialQ);
  const [tail, setTail] = useState(true);
  const [loading, setLoading] = useState<"reload" | "older" | null>(null);
  const [exhausted, setExhausted] = useState(initial.length < PAGE);
  const seq = useRef(0);
  const request = useRef(0);

  const reload = async (nextLevel: string, nextQ: string) => {
    const id = ++request.current;
    setLevel(nextLevel);
    setQ(nextQ);
    syncUrl(nextLevel, nextQ);
    setLoading("reload");
    try {
      const list = await fetchLogs(nextLevel, nextQ);
      if (id !== request.current) return;
      setRows(list);
      setExhausted(list.length < PAGE);
    } catch (err) {
      if (id === request.current) toast((err as Error).message, "error");
    } finally {
      if (id === request.current) setLoading(null);
    }
  };

  useEffect(() => {
    const next = search.trim();
    if (next === q) return;
    const id = setTimeout(() => reload(level, next), 350);
    return () => clearTimeout(id);
  }, [search]);

  const state = useEvents((e) => {
    if (e.kind !== "log" || !tail) return;
    const d = e.data;
    if (LEVELS.indexOf(d.level) < LEVELS.indexOf(level)) return;
    if (q && !d.message.toLowerCase().includes(q.toLowerCase())) return;
    seq.current -= 1;
    setRows((list) => [{ id: seq.current, at: d.at, level: d.level, source: d.source, message: d.message, process: d.process, live: true }, ...list].slice(0, KEEP));
  });

  const older = async () => {
    const oldest = [...rows].reverse().find((r) => r.id > 0);
    if (!oldest) return;
    setLoading("older");
    try {
      const more = await fetchLogs(level, q, oldest.id);
      setRows((list) => [...list, ...more]);
      if (more.length < PAGE) setExhausted(true);
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setLoading(null);
    }
  };

  const paged = usePaged(rows, 50);
  const last = paged.page >= paged.pages;

  return (
    <Panel>
      <header className="flex flex-col gap-2 border-b border-border px-4 py-3 md:flex-row md:items-center">
        <div className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" strokeWidth={1.75} />
          <Input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar nos logs" aria-label="Buscar nos logs" className="pl-9" />
        </div>
        <div className="flex items-center gap-2">
          <Select aria-label="Nível mínimo" value={level} onChange={(v) => reload(v, q)} options={OPTIONS} className="w-full md:w-36" />
          <Button variant={tail ? "outline" : "ghost"} onClick={() => setTail((v) => !v)} aria-pressed={tail} className="shrink-0">
            {tail ? <Pause className="size-4" strokeWidth={1.75} /> : <Play className="size-4" strokeWidth={1.75} />}
            {tail ? "Pausar" : "Ao vivo"}
          </Button>
        </div>
      </header>
      <div className="flex items-center justify-between border-b border-border-subtle px-4 py-2 text-[12px] text-secondary">
        <span className="inline-flex items-center gap-2">
          {loading === "reload" && <span aria-hidden className="size-3 animate-spin rounded-full border-2 border-current/30 border-t-current" />}
          {rows.length} linhas{q && <> · filtro <span className="font-mono">“{q}”</span></>}
        </span>
        <span className="inline-flex items-center gap-2">
          <span aria-hidden className={cn("size-1.5 rounded-full", tail && state === "live" ? "live-dot bg-status-ok" : "bg-muted-foreground")} />
          {tail ? STREAM_LABEL[state] : "pausado"}
        </span>
      </div>
      {rows.length === 0 ? (
        <EmptyState icon={TextSearch} title="Nenhum log com esses filtros" text="Mude o nível ou a busca; novos logs chegam aqui ao vivo." />
      ) : (
        <ol className={cn("divide-y divide-border-subtle transition-opacity", loading === "reload" && "opacity-60")}>{paged.rows.map((row) => <LogRow key={row.id} row={row} />)}</ol>
      )}
      <Pager paging={paged} noun={["linha", "linhas"]} />
      {rows.length > 0 && last && (
        <footer className="flex min-h-12 items-center justify-center border-t border-border px-4 py-2">
          {exhausted ? (
            <span className="text-[13px] text-muted-foreground">Fim dos logs guardados.</span>
          ) : (
            <Button variant="ghost" size="sm" loading={loading === "older"} disabled={loading !== null} onClick={older}>
              {loading !== "older" && <ChevronDown className="size-4" strokeWidth={1.75} />}
              Carregar mais antigos
            </Button>
          )}
        </footer>
      )}
    </Panel>
  );
}
