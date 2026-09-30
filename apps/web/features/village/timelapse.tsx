"use client";

import { ArrowUp, ChevronLeft, ChevronRight, Film, Pause, Play } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel, PanelBody, PanelHeader } from "@/components/ui/panel";
import { SegmentedControl } from "@/components/ui/segmented";
import type { Schemas } from "@/lib/api";
import { num, short, when } from "@/lib/format";

type Frame = Schemas["FrameOut"];
type Speed = "0.5" | "1" | "2" | "4";

const SPEEDS: { id: Speed; label: string }[] = [
  { id: "0.5", label: "0.5x" },
  { id: "1", label: "1x" },
  { id: "2", label: "2x" },
  { id: "4", label: "4x" },
];
const FRAME_MS = 1000;
const PRELOAD_AHEAD = 3;

function frameUrl(id: number): string {
  return `/api/v1/frames/${id}.jpg`;
}

function isField(target: EventTarget): boolean {
  return target instanceof HTMLElement && (target.tagName === "INPUT" || target.tagName === "BUTTON" || target.getAttribute("role") === "radio");
}

export function VillageTimelapse({ frames }: { frames: Frame[] }) {
  const last = frames.length - 1;
  const [index, setIndex] = useState(last);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<Speed>("1");
  const preloaded = useRef(new Set<number>());

  const current = frames[Math.min(Math.max(index, 0), last)];

  const go = useCallback((to: number) => setIndex(Math.min(Math.max(to, 0), last)), [last]);

  const toggle = useCallback(() => {
    if (playing) return setPlaying(false);
    if (index >= last) setIndex(0);
    setPlaying(true);
  }, [playing, index, last]);

  useEffect(() => {
    if (index > last) setIndex(last);
  }, [index, last]);

  useEffect(() => {
    if (!playing) return;
    if (index >= last) {
      setPlaying(false);
      return;
    }
    const timer = setTimeout(() => setIndex((i) => Math.min(i + 1, last)), FRAME_MS / Number(speed));
    return () => clearTimeout(timer);
  }, [playing, index, last, speed]);

  useEffect(() => {
    for (let i = index - 1; i <= index + PRELOAD_AHEAD; i++) {
      const frame = frames[i];
      if (!frame || preloaded.current.has(frame.id)) continue;
      preloaded.current.add(frame.id);
      const image = new Image();
      image.src = frameUrl(frame.id);
    }
  }, [index, frames]);

  if (!current) {
    return (
      <Panel>
        <PanelHeader title={<><Film className="size-4 text-secondary" strokeWidth={1.75} />Timelapse</>} />
        <EmptyState icon={Film} title="Nenhuma foto da aldeia ainda" text="As imagens começam a ser guardadas nas próximas sincronizações." />
      </Panel>
    );
  }

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === " " && !isField(event.target)) {
      event.preventDefault();
      toggle();
    } else if (event.key === "ArrowLeft" && !isField(event.target)) {
      event.preventDefault();
      setPlaying(false);
      go(index - 1);
    } else if (event.key === "ArrowRight" && !isField(event.target)) {
      event.preventDefault();
      setPlaying(false);
      go(index + 1);
    }
  };

  const position = Math.min(Math.max(index, 0), last);

  return (
    <Panel>
      <PanelHeader
        title={<><Film className="size-4 text-secondary" strokeWidth={1.75} />Timelapse</>}
        description="Fotos da aldeia a cada sincronização em que um edifício sobe ou o intervalo passa."
        aside={<Badge>{num(frames.length)} {frames.length === 1 ? "foto" : "fotos"}</Badge>}
      />
      <PanelBody>
        <div
          role="region"
          aria-label="Timelapse da aldeia. Espaço inicia ou pausa, setas mudam de foto."
          tabIndex={0}
          onKeyDown={onKeyDown}
          className="space-y-4 rounded-md focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground"
        >
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(240px,1fr)]">
            <div className="overflow-hidden rounded-md border border-border bg-background">
              <img
                key={current.id}
                src={frameUrl(current.id)}
                alt={`Aldeia em ${when(current.taken_at)}, ${num(current.points)} pontos`}
                width={current.width}
                height={current.height}
                className="block h-auto w-full"
                style={{ aspectRatio: `${current.width} / ${current.height}` }}
                decoding="async"
              />
            </div>

            <div aria-live={playing ? "off" : "polite"} className="space-y-3 text-sm">
              <div>
                <div className="text-[12px] text-muted-foreground">Foto {num(position + 1)} de {num(frames.length)}</div>
                <div className="font-medium">{when(current.taken_at)}</div>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-lg font-semibold tabular-nums">{num(current.points)}</span>
                <span className="text-secondary">pontos</span>
                {current.points_gained > 0 && <Badge tone="success">+{num(current.points_gained)}</Badge>}
              </div>
              <div>
                <div className="mb-1 text-[12px] text-muted-foreground">O que subiu desde a foto anterior</div>
                {current.diff.length ? (
                  <ul className="space-y-1">
                    {current.diff.map((d) => (
                      <li key={d.name} className="flex items-center gap-2">
                        <ArrowUp className="size-3.5 shrink-0 text-status-ok" strokeWidth={2} aria-hidden />
                        <span className="min-w-0 flex-1 truncate">{d.label}</span>
                        <span className="font-mono text-[12px] tabular-nums text-secondary">{d.before} → {d.after}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-secondary">{position === 0 ? "Primeira foto guardada." : "Nenhum edifício subiu."}</p>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <input
              type="range"
              min={0}
              max={last}
              step={1}
              value={position}
              disabled={last === 0}
              onChange={(event) => {
                setPlaying(false);
                go(Number(event.target.value));
              }}
              aria-label="Posição no tempo"
              aria-valuetext={`Foto ${position + 1} de ${frames.length}, ${short(current.taken_at)}`}
              className="w-full accent-foreground disabled:opacity-40"
            />
            <div className="flex justify-between font-mono text-[11px] text-muted-foreground">
              <span>{short(frames[0].taken_at)}</span>
              <span>{short(frames[last].taken_at)}</span>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="flex items-center gap-2">
                <Button variant="outline" size="icon" onClick={() => { setPlaying(false); go(position - 1); }} disabled={position === 0} aria-label="Foto anterior">
                  <ChevronLeft className="size-4" />
                </Button>
                <Button onClick={toggle} disabled={last === 0} aria-pressed={playing} className="min-w-28">
                  {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
                  {playing ? "Pausar" : "Reproduzir"}
                </Button>
                <Button variant="outline" size="icon" onClick={() => { setPlaying(false); go(position + 1); }} disabled={position === last} aria-label="Próxima foto">
                  <ChevronRight className="size-4" />
                </Button>
              </div>
              <SegmentedControl label="Velocidade" value={speed} options={SPEEDS} onChange={setSpeed} className="sm:ml-auto sm:h-9 sm:w-60" />
            </div>
          </div>
        </div>
      </PanelBody>
    </Panel>
  );
}
