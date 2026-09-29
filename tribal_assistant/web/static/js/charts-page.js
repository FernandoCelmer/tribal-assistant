import { AGENTS, Api, Format, Theme } from "/static/js/core.js";
import { HorizontalBars, Lines, StackedBars } from "/static/js/charts.js";

class MetricsPanel {
  constructor(api) {
    this.api = api;
    this.hours = 24;
    this.kpis = document.getElementById("kpis");
    this.hourly = new StackedBars(document.getElementById("hourly-chart"), { height: 220, format: (v) => Format.number.format(v) });
    this.refusals = new HorizontalBars(document.getElementById("refusal-chart"), { format: (v) => Format.number.format(v) });
    this.legend = document.getElementById("hourly-legend");
    this.table = document.getElementById("hourly-table");
    this.data = null;
    this.config = null;

    for (const btn of document.querySelectorAll("[data-hours]")) {
      btn.addEventListener("click", () => {
        this.hours = Number(btn.dataset.hours);
        document.querySelectorAll("[data-hours]").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
        this.load();
      });
    }
  }

  async load() {
    try {
      this.data = await this.api.get(`/agents/stats?hours=${this.hours}`);
    } catch {
      return;
    }
    this.render();
  }

  render() {
    const d = this.data;
    if (!d) return;

    const tiles = [
      ["Rodadas", d.runs, d.runs_failed ? `${d.runs_failed} com falha` : "nenhuma falha"],
      ["Ações feitas", d.actions_ok, "construções, tropas, saques, missões"],
      ["Recusadas pelas travas", d.actions_refused, "segurança funcionando"],
      ["Falhas no jogo", d.actions_failed, "o jogo não aceitou"],
      ["Construções", d.builds, "na fila"],
      ["Recrutamentos", d.recruits, "lotes"],
      ["Saques", d.attacks, "ataques enviados"],
      ["Missões", d.quests, "concluídas ou coletadas"],
      ["Tokens de IA", d.tokens_in + d.tokens_out, `${Format.number.format(d.tokens_in)} entrada · ${Format.number.format(d.tokens_out)} saída`],
    ];
    this.kpis.innerHTML = tiles.map(([label, value, sub]) => `<div class="kpi"><dt class="kpi__label">${label}</dt><dd class="kpi__value">${Format.number.format(value)}</dd><dd class="kpi__sub">${sub}</dd></div>`).join("");

    const present = AGENTS.filter((a) => d.hourly.some((h) => h.by_agent[a.key]));
    const hours = d.hourly.map((h) => Format.date(h.hour));
    const daily = this.hours > 48;
    const labels = hours.map((t) => daily ? t.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) : `${String(t.getHours()).padStart(2, "0")}h`);
    const series = present.map((a) => ({ name: a.label, color: Theme.color(a.slot), values: d.hourly.map((h) => h.by_agent[a.key] || 0) }));

    this.legend.innerHTML = present.map((a) => `<li><i style="background: var(--series-${a.slot})"></i>${a.label}</li>`).join("");
    this.hourly.render({ labels, series, tooltipTitle: (i) => hours[i].toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) });
    this.refusals.render({ rows: d.refusals, color: Theme.token("--color-text-muted") });

    this.table.innerHTML = `<table class="table"><thead><tr><th>Hora</th>${present.map((a) => `<th class="num">${a.label}</th>`).join("")}</tr></thead><tbody>${d.hourly.filter((h) => Object.keys(h.by_agent).length).map((h, i) => `<tr><td>${Format.short(h.hour)}</td>${present.map((a) => `<td class="num">${h.by_agent[a.key] || 0}</td>`).join("")}</tr>`).join("") || '<tr><td class="empty">Sem ações</td></tr>'}</tbody></table>`;

      }
}

class EvolutionPanel {
  constructor(api) {
    this.api = api;
    this.village = document.getElementById("history-village");
    this.hours = document.getElementById("history-hours");
    this.points = new Lines(document.getElementById("points-chart"), { height: 220, format: (v) => Format.number.format(v) });
    this.resources = new Lines(document.getElementById("resources-chart"), { height: 220, format: (v) => Format.number.format(v) });
    this.legend = document.getElementById("resources-legend");
    this.rows = [];
    this.village.addEventListener("change", () => this.load());
    this.hours.addEventListener("change", () => this.load());
  }

  async init() {
    try {
      const overview = await this.api.get("/game/overview");
      this.village.innerHTML = overview.villages.map((v) => `<option value="${v.id}">${Format.esc(v.name)} (${Format.esc(v.coords)})</option>`).join("");
    } catch {
      return;
    }
    await this.load();
  }

  async load() {
    if (!this.village.value) return this.render();
    try {
      this.rows = await this.api.get(`/game/history?village_id=${this.village.value}&hours=${this.hours.value}`);
    } catch {
      this.rows = [];
    }
    this.render();
  }

  render() {
    const times = this.rows.map((r) => Format.date(r.taken_at));
    this.points.render({ times, series: [{ name: "Pontos", color: Theme.color(1), values: this.rows.map((r) => r.points) }] });

    const resources = [
      { name: "Madeira", color: Theme.token("--color-resource-wood"), key: "wood" },
      { name: "Argila", color: Theme.token("--color-resource-clay"), key: "clay" },
      { name: "Ferro", color: Theme.token("--color-resource-iron"), key: "iron" },
    ];
    this.legend.innerHTML = resources.map((r) => `<li><i style="background:${r.color}"></i>${r.name}</li>`).join("");
    this.resources.render({ times, series: resources.map((r) => ({ name: r.name, color: r.color, values: this.rows.map((row) => row[r.key]) })) });
  }
}

class ChartsPage {
  constructor() {
    this.api = new Api();
    this.metrics = new MetricsPanel(this.api);
    this.evolution = new EvolutionPanel(this.api);
  }

  async start() {
    for (const btn of document.querySelectorAll("[data-table-toggle]")) {
      btn.addEventListener("click", () => {
        const target = document.getElementById(btn.dataset.tableToggle);
        target.hidden = !target.hidden;
        btn.textContent = target.hidden ? "ver tabela" : "ocultar tabela";
      });
    }

    Theme.onChange(() => { this.metrics.render(); this.evolution.render(); });
    await Promise.all([this.metrics.load(), this.evolution.init()]);

    setInterval(() => this.metrics.load(), 60000);
    setInterval(() => this.evolution.load(), 120000);
    addEventListener("resize", () => { this.metrics.render(); this.evolution.render(); });
  }
}

new ChartsPage().start();
