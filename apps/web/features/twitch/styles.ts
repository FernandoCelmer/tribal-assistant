export const TWITCH_CSS = `
.tw-root {
  --bg: #080A0B;
  --panel: #111416;
  --inner: #15191C;
  --line: #282D31;
  --text: #F3F4F6;
  --text-2: #A3A8AE;
  --text-3: #737A82;
  --green: #22C55E;
  --yellow: #FACC15;
  --red: #EF4444;
  --head: 46px;
  --node: 34px;
  --node-gap: 14px;
  --row: 36px;
  position: fixed; inset: 0; overflow: hidden; background: var(--bg); color: var(--text);
  font-family: var(--font-sans, Inter, system-ui, sans-serif); font-size: 15px;
  display: flex; align-items: center; justify-content: center;
}
.tw-root[data-transparent] { background: transparent; }
.tw-root * { box-sizing: border-box; }
.tw-root h2 { margin: 0; font-size: 18px; font-weight: 600; }
.tw-secondary { color: var(--text-2); font-weight: 400; }
.tw-muted { color: var(--text-3); margin: 0; }
.tw-count { color: var(--yellow); font-weight: 600; font-variant-numeric: tabular-nums; }
.tw-truncate { min-width: 0; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.tw-header { height: 100%; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 16px; padding: 0 16px; background: var(--panel); border: 1px solid var(--line); border-radius: 12px; white-space: nowrap; }
.tw-header-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
.tw-header-center { font-weight: 600; text-align: center; }
.tw-header-right { display: flex; justify-content: flex-end; align-items: baseline; gap: 8px; font-size: 1.1em; }
.tw-live-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--green); animation: tw-pulse 1.8s ease-in-out infinite; }
.tw-live { padding: 3px 12px; border-radius: 999px; font-weight: 700; color: var(--green); background: color-mix(in srgb, var(--green) 12%, transparent); border: 1px solid color-mix(in srgb, var(--green) 45%, transparent); }
.tw-village { font-size: 1.2em; }
.tw-chip { padding: 3px 10px; border-radius: 999px; border: 1px solid var(--line); color: var(--text-2); font-size: 0.9em; }
.tw-alert { color: #fff; background: var(--red); padding: 4px 14px; border-radius: 999px; font-weight: 700; }

.tw-game { border: 1px solid var(--line); border-radius: 12px; background: transparent; min-height: 0; height: 100%; }
.tw-decision { padding-top: 8px; padding-bottom: 8px; }

.tw-panel { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.tw-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: var(--head); padding: 0 16px; border-bottom: 1px solid var(--line); }
.tw-body { padding: 12px 16px; min-height: 0; flex: 1; overflow: hidden; }
.tw-moves .tw-body, .tw-activity .tw-body { overflow-y: auto; }
.tw-flow .tw-body { padding: 0; display: flex; }

.tw-score { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 10px; }
.tw-score strong { font-size: 30px; font-weight: 700; font-variant-numeric: tabular-nums; }
.tw-protect { color: var(--green); border: 1px solid color-mix(in srgb, var(--green) 45%, transparent); background: color-mix(in srgb, var(--green) 10%, transparent); padding: 4px 12px; border-radius: 999px; font-weight: 600; }
.tw-resources { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.tw-rank { margin-left: 10px; }
.tw-resource { display: flex; align-items: center; gap: 8px; background: var(--inner); border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; }
.tw-resource b { font-size: 1.1em; }
.tw-pop-icon { color: #a78bfa; }

.tw-decision { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.tw-decision > div { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.tw-decision strong { font-size: 1.15em; }
.tw-state { flex: none; padding: 3px 12px; border-radius: 999px; border: 1px solid var(--line); color: var(--text-2); font-weight: 600; font-size: 0.9em; }
.tw-state[data-status="running"], .tw-state[data-status="deferred"] { color: var(--yellow); border-color: color-mix(in srgb, var(--yellow) 55%, transparent); }
.tw-state[data-status="ok"] { color: var(--green); border-color: color-mix(in srgb, var(--green) 50%, transparent); }
.tw-state[data-status="failed"] { color: var(--red); border-color: color-mix(in srgb, var(--red) 50%, transparent); }

.tw-list { list-style: none; margin: 0; overflow-y: auto; }
.tw-list li { display: flex; align-items: center; gap: 10px; min-height: var(--row); border-bottom: 1px solid var(--line); }
.tw-moves .tw-body { padding-top: 4px; padding-bottom: 4px; }
.tw-list li:last-child { border-bottom: 0; }
.tw-list li[data-incoming] { color: var(--red); }

.tw-highlights .tw-head { justify-content: space-between; }
.tw-pager { display: flex; gap: 4px; }
.tw-pager i { width: 6px; height: 6px; border-radius: 50%; background: var(--line); }
.tw-pager i[data-on] { background: var(--yellow); }
.tw-slide { animation: tw-fade .5s ease-out; display: flex; flex-direction: column; gap: 8px; }
.tw-grid-2 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px 16px; }
.tw-metric span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tw-metric { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; border-bottom: 1px solid var(--line); padding: 3px 0; }
.tw-metric strong { order: 2; font-size: 1.1em; font-variant-numeric: tabular-nums; }
.tw-metric span { color: var(--text-2); }
.tw-lines { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.tw-lines li { line-height: 1.35; }
.tw-learning { display: flex; flex-direction: column; gap: 8px; }
.tw-learning p { margin: 0; line-height: 1.35; }
.tw-learning code { font-family: var(--font-mono, ui-monospace, monospace); color: var(--text-2); }
.tw-accent { color: #c4b5fd; }
.tw-bars { display: flex; flex-direction: column; gap: 6px; margin-top: 4px; }
.tw-bar-row { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr) auto; align-items: center; gap: 10px; }
.tw-bar-row > span:first-child { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tw-bar { height: 6px; border-radius: 3px; background: var(--inner); border: 1px solid var(--line); overflow: hidden; }
.tw-bar > span { display: block; height: 100%; background: var(--green); transition: width 1s linear; }
.tw-raid { display: flex; gap: 12px; align-items: flex-start; }
.tw-raid p { margin: 4px 0 0; color: var(--text-2); }
.tw-raid-dot { width: 14px; height: 14px; border-radius: 50%; margin-top: 3px; background: var(--text-3); flex: none; }
.tw-raid[data-result="green"] .tw-raid-dot { background: var(--green); }
.tw-raid[data-result="yellow"] .tw-raid-dot { background: var(--yellow); }
.tw-raid[data-result="red"] .tw-raid-dot { background: var(--red); }
.tw-raid[data-result="blue"] .tw-raid-dot { background: #60a5fa; }
.tw-chart { display: flex; flex-direction: column; gap: 6px; height: 100%; }
.tw-chart svg { flex: 1; width: 100%; min-height: 60px; }
.tw-chart polyline { fill: none; stroke-width: 2; }
.tw-line-wood { stroke: #c08a4e; }
.tw-line-clay { stroke: #d06a45; }
.tw-line-iron { stroke: #9fb0c4; }
.tw-legend { display: flex; gap: 14px; font-size: 0.85em; }
.tw-legend-wood { color: #c08a4e; }
.tw-legend-clay { color: #d06a45; }
.tw-legend-iron { color: #9fb0c4; }
.tw-map { width: 100%; height: 100%; min-height: 80px; }
.tw-map-barb { fill: var(--text-3); }
.tw-map-player { fill: #60a5fa; }
.tw-map-own { fill: var(--yellow); }
.tw-map-route { stroke: #3a4046; stroke-width: 0.6; stroke-dasharray: 2 2; }
.tw-map-troop { fill: var(--green); }
.tw-protection { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; height: 100%; }
.tw-protection strong { font-size: 2.2em; }
.tw-protection[data-close] strong { color: var(--red); }

.tw-flow { min-height: 0; }
.tw-graph { position: relative; flex: 1; width: 100%; min-height: 0; display: grid; grid-template-columns: auto minmax(40px, 1fr) auto minmax(40px, 1fr) minmax(220px, 26%); align-items: center; padding: 10px 16px; }
.tw-edges { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; overflow: visible; }
.tw-edge { fill: none; stroke-width: 1.6; transition: stroke .3s; }
.tw-edge-idle { stroke: #30363b; }
.tw-edge-active { stroke: var(--green); }
.tw-edge-chosen { stroke: var(--yellow); stroke-width: 2; }
.tw-arrow-idle { fill: #30363b; }
.tw-arrow-active { fill: var(--green); }
.tw-arrow-chosen { fill: var(--yellow); }
.tw-agents { grid-column: 1; display: flex; gap: 56px; position: relative; z-index: 1; }
.tw-agent-column { display: flex; flex-direction: column; gap: var(--node-gap); }
.tw-agent-column[data-offset] { padding-top: calc((var(--node) + var(--node-gap)) / 2); }
.tw-node { display: flex; align-items: center; gap: 10px; height: var(--node); padding: 0 10px; background: var(--inner); border: 1px solid var(--line); border-radius: 8px; color: var(--text-2); white-space: nowrap; transition: border-color .3s, color .3s; position: relative; z-index: 1; }
.tw-agents .tw-node { width: 180px; }
.tw-node-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.tw-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--text-3); flex: none; }
.tw-node[data-on] { border-color: color-mix(in srgb, var(--green) 60%, transparent); color: var(--text); }
.tw-node[data-on] .tw-dot { background: var(--green); }
.tw-hub { grid-column: 3; width: 136px; aspect-ratio: 1; border-radius: 50%; background: var(--inner); border: 2px solid #3a4046; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; position: relative; z-index: 1; }
.tw-hub svg { color: var(--yellow); }
.tw-hub span { color: var(--text-2); font-size: 0.85em; }
.tw-proposals { grid-column: 5; display: flex; flex-direction: column; gap: calc(var(--node-gap) * 0.55); position: relative; z-index: 1; min-width: 0; }
.tw-proposal[data-chosen] { border-color: var(--yellow); color: var(--text); }
.tw-proposal[data-status="ok"]:not([data-chosen]) { color: var(--text); }
.tw-badge { flex: none; font-size: 0.8em; padding: 1px 8px; border-radius: 999px; border: 1px solid var(--line); color: var(--text-2); }
.tw-badge[data-status="deferred"], .tw-badge[data-status="running"] { color: var(--yellow); border-color: color-mix(in srgb, var(--yellow) 55%, transparent); }
.tw-badge[data-status="ok"] { color: var(--green); border-color: color-mix(in srgb, var(--green) 50%, transparent); }
.tw-badge[data-status="failed"] { color: var(--red); border-color: color-mix(in srgb, var(--red) 50%, transparent); }
.tw-empty { color: var(--text-3); }

.tw-events { list-style: none; margin: 0; overflow-y: auto; }
.tw-events li { display: grid; grid-template-columns: 48px 1fr; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--line); line-height: 1.35; animation: tw-fade .4s ease-out; }
.tw-events li:last-child { border-bottom: 0; }
.tw-events time { color: var(--text-3); font-variant-numeric: tabular-nums; }
.tw-events li[data-bad] span { color: var(--red); }

@keyframes tw-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .4; } }
@keyframes tw-fade { from { opacity: 0; } to { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .tw-root *, .tw-root { animation: none !important; transition: none !important; } }

`;
