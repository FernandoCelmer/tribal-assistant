import { Api, Format, Theme } from "/static/js/core.js";

const SVG_NS = "http://www.w3.org/2000/svg";

const TOOL_LABELS = {
  get_village_state: "ler estado da aldeia",
  get_quests: "ler missões",
  lookup_knowledge: "consultar regras do jogo",
  list_barbarians: "listar bárbaras",
  upgrade_building: "construir",
  recruit_units: "recrutar",
  send_farm_attack: "saquear bárbara",
  send_scavenge: "enviar coleta",
  unlock_scavenge: "desbloquear coleta",
  claim_quest_rewards: "coletar recompensas",
  complete_quest: "concluir missão",
  set_village_goal: "definir objetivo",
};

const OUTCOMES = {
  ok: { label: "feito", token: "--color-success" },
  refused: { label: "recusado pela trava", token: "--color-warning" },
  failed: { label: "erro no jogo", token: "--color-danger" },
};

class FlowGraph {
  constructor(host) {
    this.host = host;
    this.host.classList.add("chart", "flow");
    this.svg = document.createElementNS(SVG_NS, "svg");
    this.svg.setAttribute("role", "img");
    this.svg.setAttribute("aria-label", "Fluxo de agentes para ferramentas e resultados");
    this.host.appendChild(this.svg);

    this.tooltip = document.createElement("div");
    this.tooltip.className = "chart__tooltip";
    this.tooltip.hidden = true;
    this.host.appendChild(this.tooltip);
  }

  el(name, attrs = {}, parent = this.svg) {
    const node = document.createElementNS(SVG_NS, name);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    parent.appendChild(node);
    return node;
  }

  layout(nodes, x, top, height, gap, scale) {
    let y = top;
    const out = {};
    for (const node of nodes) {
      const h = Math.max(4, node.count * scale);
      out[node.id] = { ...node, x, y, h, outY: y, inY: y };
      y += h + gap;
    }
    return out;
  }

  band(x0, y0, x1, y1, h) {
    const mid = (x0 + x1) / 2;
    return `M${x0},${y0} C${mid},${y0} ${mid},${y1} ${x1},${y1} L${x1},${y1 + h} C${mid},${y1 + h} ${mid},${y0 + h} ${x0},${y0 + h} Z`;
  }

  tip(html, e) {
    const box = this.host.getBoundingClientRect();
    this.tooltip.innerHTML = html;
    this.tooltip.hidden = false;
    const tip = this.tooltip.getBoundingClientRect();
    let left = e.clientX - box.left + 14;
    if (left + tip.width > box.width) left = e.clientX - box.left - tip.width - 14;
    this.tooltip.style.left = `${Math.max(0, left)}px`;
    this.tooltip.style.top = `${Math.max(0, e.clientY - box.top - tip.height / 2)}px`;
  }

  render(data) {
    this.svg.innerHTML = "";
    const width = Math.max(320, this.host.clientWidth || 900);

    if (!data || !data.calls) {
      this.svg.setAttribute("viewBox", `0 0 ${width} 160`);
      const t = this.el("text", { x: width / 2, y: 80, "text-anchor": "middle", class: "chart__empty" });
      t.textContent = "Nenhuma ferramenta usada no período. Rode uma rodada de agentes.";
      return;
    }

    const narrow = width < 640;
    const nodeW = 12;
    const gap = 12;
    const rows = Math.max(data.agents.length, data.tools.length, data.outcomes.length);
    const height = Math.max(320, rows * 44);
    const top = 16;
    const usable = height - top * 2;
    const scale = Math.min(...[data.agents, data.tools, data.outcomes].map((col) => (usable - gap * (col.length - 1)) / col.reduce((s, n) => s + n.count, 0)));

    const labelW = narrow ? 96 : 150;
    const xAgents = 0;
    const xTools = narrow ? width * 0.42 : width * 0.45;
    const xOutcomes = width - nodeW - (narrow ? 96 : 150);

    this.svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    this.svg.setAttribute("height", height);

    const agents = this.layout(data.agents, xAgents, top, usable, gap, scale);
    const tools = this.layout(data.tools, xTools, top, usable, gap, scale);
    const outcomes = this.layout(data.outcomes, xOutcomes, top, usable, gap, scale);

    const links = this.el("g", { class: "flow__links" });

    for (const link of data.agent_tool) {
      const a = agents[link.source];
      const t = tools[link.target];
      if (!a || !t) continue;
      const h = link.count * scale;
      const meta = Format.agent(link.source);
      const path = this.el("path", { d: this.band(a.x + nodeW, a.outY, t.x, t.inY, h), fill: Theme.color(meta.slot), class: "flow__link", "data-agent": link.source, "data-tool": link.target }, links);
      path.addEventListener("mousemove", (e) => this.tip(`<div class="chart__tip-title">${meta.label} → ${TOOL_LABELS[link.target] || link.target}</div><div class="chart__tip-row">chamadas<b>${Format.number.format(link.count)}</b></div>`, e));
      path.addEventListener("mouseleave", () => { this.tooltip.hidden = true; });
      a.outY += h;
      t.inY += h;
    }

    for (const link of data.tool_outcome) {
      const t = tools[link.source];
      const o = outcomes[link.target];
      if (!t || !o) continue;
      const h = link.count * scale;
      const outcome = OUTCOMES[link.target] || { label: link.target, token: "--color-text-muted" };
      const path = this.el("path", { d: this.band(t.x + nodeW, t.outY, o.x, o.inY, h), fill: Theme.token(outcome.token), class: "flow__link", "data-tool": link.source }, links);
      path.addEventListener("mousemove", (e) => this.tip(`<div class="chart__tip-title">${TOOL_LABELS[link.source] || link.source} → ${outcome.label}</div><div class="chart__tip-row">vezes<b>${Format.number.format(link.count)}</b></div>`, e));
      path.addEventListener("mouseleave", () => { this.tooltip.hidden = true; });
      t.outY += h;
      o.inY += h;
    }

    const nodes = this.el("g", { class: "flow__nodes" });
    const label = (x, y, text, sub, anchor) => {
      const t = this.el("text", { x, y, "text-anchor": anchor, class: "chart__label chart__label--halo" }, nodes);
      t.textContent = text;
      const s = this.el("tspan", { class: "flow__count", dx: 6 }, t);
      s.textContent = sub;
    };

    for (const a of Object.values(agents)) {
      const meta = Format.agent(a.id);
      this.el("rect", { x: a.x, y: a.y, width: nodeW, height: a.h, rx: 3, fill: Theme.color(meta.slot), class: "flow__node" }, nodes);
      label(a.x + nodeW + 8, a.y + Math.min(a.h / 2 + 4, 14), meta.label, Format.number.format(a.count), "start");
    }

    for (const t of Object.values(tools)) {
      this.el("rect", { x: t.x, y: t.y, width: nodeW, height: t.h, rx: 3, class: "flow__node flow__node--tool" }, nodes);
      label(t.x + nodeW + 8, t.y + Math.min(t.h / 2 + 4, 14), TOOL_LABELS[t.id] || t.id, Format.number.format(t.count), "start");
    }

    for (const o of Object.values(outcomes)) {
      const outcome = OUTCOMES[o.id] || { label: o.id, token: "--color-text-muted" };
      this.el("rect", { x: o.x, y: o.y, width: nodeW, height: o.h, rx: 3, fill: Theme.token(outcome.token), class: "flow__node" }, nodes);
      label(o.x + nodeW + 8, o.y + Math.min(o.h / 2 + 4, 14), outcome.label, Format.number.format(o.count), "start");
    }

    for (const path of links.querySelectorAll(".flow__link")) {
      path.addEventListener("mouseenter", () => {
        const agent = path.dataset.agent;
        const tool = path.dataset.tool;
        links.classList.add("is-focused");
        for (const other of links.querySelectorAll(".flow__link")) {
          const related = agent ? other.dataset.agent === agent || (!other.dataset.agent && other.dataset.tool === tool) : other.dataset.tool === tool;
          other.classList.toggle("is-active", related);
        }
      });
      path.addEventListener("mouseleave", () => {
        links.classList.remove("is-focused");
        links.querySelectorAll(".is-active").forEach((p) => p.classList.remove("is-active"));
      });
    }
  }
}

class FlowPage {
  constructor() {
    this.api = new Api();
    this.graph = new FlowGraph(document.getElementById("flow-chart"));
    this.hours = 24;
    this.run = document.getElementById("flow-run");
    this.meta = document.getElementById("flow-meta");
    this.table = document.getElementById("flow-table");
    this.data = null;
  }

  async start() {
    for (const btn of document.querySelectorAll("[data-hours]")) {
      btn.addEventListener("click", () => {
        this.hours = Number(btn.dataset.hours);
        document.querySelectorAll("[data-hours]").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
        this.run.value = "";
        this.load();
      });
    }

    this.run.addEventListener("change", () => this.load());
    document.getElementById("flow-table-toggle").addEventListener("click", (e) => {
      this.table.hidden = !this.table.hidden;
      e.currentTarget.textContent = this.table.hidden ? "ver tabela" : "ocultar tabela";
    });

    Theme.onChange(() => this.graph.render(this.data));
    addEventListener("resize", () => this.graph.render(this.data));

    await this.loadRuns();
    await this.load();
    setInterval(() => this.load(), 60000);
  }

  async loadRuns() {
    const runs = await this.api.get("/agents/runs?limit=50").catch(() => []);
    this.run.innerHTML = `<option value="">todas as rodadas do período</option>` + runs.map((r) => `<option value="${r.run_id}">${Format.short(r.started_at)} · ${r.brain === "llm" ? Format.esc(r.model || "IA") : "regras"}${r.dry_run ? " · simulação" : ""}</option>`).join("");
  }

  async load() {
    const params = new URLSearchParams({ hours: this.hours });
    if (this.run.value) params.set("run_id", this.run.value);

    try {
      this.data = await this.api.get(`/agents/flow?${params}`);
    } catch {
      return;
    }

    this.meta.textContent = `${Format.number.format(this.data.calls)} chamadas de ferramenta em ${this.data.runs} rodada(s)`;
    this.graph.render(this.data);
    this.renderTable();
  }

  renderTable() {
    const d = this.data;
    if (!d) return;
    const rows = d.agent_tool.map((l) => `<tr><td>${Format.agent(l.source).label}</td><td>${TOOL_LABELS[l.target] || l.target}</td><td class="num">${Format.number.format(l.count)}</td></tr>`).join("");
    this.table.innerHTML = `<table class="table"><thead><tr><th>Agente</th><th>Ferramenta</th><th class="num">Chamadas</th></tr></thead><tbody>${rows || '<tr><td colspan="3" class="empty">Sem dados</td></tr>'}</tbody></table>`;
  }
}

new FlowPage().start();
