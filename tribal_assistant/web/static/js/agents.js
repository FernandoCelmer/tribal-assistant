import { AGENTS, API, Api, EventFeed, Format, Html, Theme, Toast } from "/static/js/core.js";

const KIND_LABELS = {
  prompt: "contexto enviado",
  thought: "raciocínio",
  tool_call: "chamou",
  tool_result: "resposta",
  summary: "resumo",
  info: "info",
  error: "erro",
};

const TRIGGERS = { schedule: "agendada", dashboard: "painel", cli: "terminal", mcp: "MCP", manual: "manual" };

class LivePanel {
  constructor(api) {
    this.api = api;
    this.root = document.getElementById("live");
    this.title = document.getElementById("live-title");
    this.detail = document.getElementById("live-detail");
    this.brain = document.getElementById("brain-meta");
    this.state = null;
  }

  async load() {
    try {
      this.state = await this.api.get("/agents/live");
    } catch {
      return;
    }
    this.render();
  }

  apply(event, data) {
    if (event === "run_started") this.state = { ...this.state, running: true, run_id: data.run_id, started_at: data.at, step: "iniciando" };
    if (event === "step" && this.state?.running) Object.assign(this.state, { village: data.village, agent: data.agent, step: `${KIND_LABELS[data.kind] || data.kind}${data.tool ? ` ${data.tool}` : ""}` });
    if (event === "run_finished") this.load();
    this.render();
  }

  setBrain(config) {
    const brain = config.brain === "llm" ? `IA: ${config.provider} · ${config.model}` : "cérebro: regras fixas";
    this.brain.textContent = brain;
  }

  render() {
    const s = this.state;
    if (!s) return;
    this.root.classList.toggle("is-running", !!s.running);
    if (s.running) {
      const agent = s.agent ? Format.agent(s.agent).label : "";
      this.title.textContent = `Rodada ${s.run_id} em andamento`;
      this.detail.textContent = [s.village, agent, s.step].filter(Boolean).join(" · ") + (s.started_at ? ` · começou ${Format.relative(s.started_at)}` : "");
      return;
    }
    this.title.textContent = s.enabled ? "Ocioso — agendamento ligado" : "Ocioso — agendamento desligado";
    this.detail.textContent = s.enabled && s.next_run_at ? `próxima rodada ${Format.relative(s.next_run_at)}` : "rode manualmente ou ligue o agendamento na configuração";
  }
}

class AgentCards {
  constructor() {
    this.root = document.getElementById("agent-cards");
  }

  render(stats, config) {
    const byKey = Object.fromEntries((stats?.agents || []).map((a) => [a.agent, a]));
    const known = (config?.agents || []).map((a) => a.key);
    const list = AGENTS.filter((a) => known.includes(a.key) || byKey[a.key]);

    this.root.innerHTML = list.map((meta) => {
      const s = byKey[meta.key];
      const rate = s && s.actions ? Math.round((s.ok / s.actions) * 100) : null;
      return `<li class="agent-card" style="--agent-color: var(--series-${meta.slot})">
        <div class="agent-card__head"><span class="agent-card__swatch" aria-hidden="true"></span><b>${meta.label}</b>
          ${rate == null ? Html.badge("sem ações") : Html.badge(`${rate}% ok`, rate >= 70 ? "success" : rate >= 40 ? "warning" : "danger")}</div>
        <p class="agent-card__area">${meta.area}</p>
        <dl class="agent-card__stats">
          <div><dt>feitas</dt><dd>${s?.ok ?? 0}</dd></div>
          <div><dt>recusadas</dt><dd>${s?.refused ?? 0}</dd></div>
          <div><dt>falhas</dt><dd>${s?.failed ?? 0}</dd></div>
        </dl>
        <p class="agent-card__last">${s?.last_action ? `<span class="muted">${Format.short(s.last_at)}</span> ${Format.esc(s.last_action.replaceAll("_", " "))}: ${Format.esc(s.last_result)}` : "<span class=\"muted\">ainda não agiu no período</span>"}</p>
      </li>`;
    }).join("");
  }
}

class RunsPanel {
  constructor(api, trace) {
    this.api = api;
    this.trace = trace;
    this.body = document.getElementById("runs-body");
    this.body.addEventListener("click", (e) => {
      const row = e.target.closest("tr[data-run]");
      if (row) this.trace.load(row.dataset.run);
    });
    this.body.addEventListener("keydown", (e) => {
      const row = e.target.closest("tr[data-run]");
      if (row && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        this.trace.load(row.dataset.run);
      }
    });
  }

  async load() {
    let runs = [];
    try {
      runs = await this.api.get("/agents/runs?limit=40");
    } catch {
      return;
    }

    this.body.innerHTML = runs.length ? runs.map((r) => {
      const seconds = r.finished_at ? (Format.date(r.finished_at) - Format.date(r.started_at)) / 1000 : (Date.now() - Format.date(r.started_at)) / 1000;
      const status = { running: Html.badge("rodando", "info"), done: Html.badge("ok", "success"), failed: Html.badge("falhou", "danger"), skipped: Html.badge("pulada"), interrupted: Html.badge("interrompida", "warning") }[r.status] || Html.badge(r.status);
      const brain = r.brain === "llm" ? Format.esc(r.model || r.provider || "IA") : "regras";
      return `<tr data-run="${r.run_id}" tabindex="0" class="${this.trace.runId === r.run_id ? "is-selected" : ""}">
        <td>${Format.short(r.started_at)}</td><td>${TRIGGERS[r.trigger] || r.trigger}</td><td>${brain}</td>
        <td>${r.dry_run ? Html.badge("simulação", "info") : Html.badge("ao vivo", "warning")}</td>
        <td class="num">${Format.duration(seconds)}</td><td class="num">${r.actions_ok}</td><td class="num">${r.actions_refused}</td>
        <td class="num">${r.actions_failed}</td><td class="num">${Format.number.format(r.tokens_in + r.tokens_out)}</td><td>${status}</td></tr>`;
    }).join("") : '<tr><td colspan="10" class="empty">Nenhuma rodada ainda. Clique em “Simular rodada”.</td></tr>';
  }
}

class TracePanel {
  constructor(api) {
    this.api = api;
    this.root = document.getElementById("trace");
    this.body = document.getElementById("trace-body");
    this.meta = document.getElementById("trace-meta");
    this.idNode = document.getElementById("trace-id");
    this.filter = document.getElementById("trace-filter");
    this.runId = null;
    this.data = null;
    this.filter.addEventListener("change", () => this.render());
    document.getElementById("trace-close").addEventListener("click", () => {
      this.root.hidden = true;
      this.runId = null;
    });
  }

  async load(runId) {
    this.runId = runId;
    try {
      this.data = await this.api.get(`/agents/runs/${runId}`);
    } catch (e) {
      return;
    }
    this.root.hidden = false;
    this.render();
    this.root.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  append(event) {
    if (!this.data || event.run_id !== this.runId) return;
    this.data.steps.push({ seq: event.seq, agent: event.agent, kind: event.kind, tool: event.tool, content: event.content, is_error: event.is_error, village_id: null, created_at: event.at });
    this.render();
  }

  keep(step) {
    const f = this.filter.value;
    if (f === "actions") return ["tool_call", "tool_result", "summary"].includes(step.kind);
    if (f === "thought") return ["thought", "summary", "prompt"].includes(step.kind);
    if (f === "errors") return step.is_error || step.content.startsWith("RECUSADO") || step.kind === "error";
    return true;
  }

  render() {
    const d = this.data;
    if (!d) return;
    const r = d.run;
    this.idNode.textContent = r.run_id;
    this.meta.textContent = `${TRIGGERS[r.trigger] || r.trigger} · ${r.brain === "llm" ? `${r.provider} ${r.model}` : "regras"} · ${r.dry_run ? "simulação" : "ao vivo"} · ${r.actions_ok} feitas, ${r.actions_refused} recusadas, ${r.actions_failed} falhas${r.error ? ` · erro: ${r.error}` : ""}`;

    const groups = [];
    for (const step of d.steps) {
      const village = step.village_id != null ? (d.villages[step.village_id] || `aldeia ${step.village_id}`) : "Rodada";
      const key = `${village}|${step.agent}`;
      let group = groups[groups.length - 1];
      if (!group || group.key !== key) {
        group = { key, village, agent: step.agent, steps: [] };
        groups.push(group);
      }
      group.steps.push(step);
    }

    const visible = groups.map((g) => ({ ...g, steps: g.steps.filter((s) => this.keep(s)) })).filter((g) => g.steps.length);
    let lastVillage = null;

    this.body.innerHTML = visible.length ? visible.map((g) => {
      const meta = Format.agent(g.agent);
      const villageHead = g.village !== lastVillage ? `<h3 class="trace__village">${Format.esc(g.village)}</h3>` : "";
      lastVillage = g.village;
      return `${villageHead}<section class="trace__agent" style="--agent-color: var(--series-${meta.slot})">
        <h4 class="trace__agent-title"><span class="agent-card__swatch" aria-hidden="true"></span>${meta.label}</h4>
        <ol class="trace__steps">${g.steps.map((s) => this.step(s)).join("")}</ol>
      </section>`;
    }).join("") : '<p class="empty">Nenhum passo com esse filtro.</p>';
  }

  step(s) {
    const refused = s.kind === "tool_result" && s.content.startsWith("RECUSADO");
    const tone = s.is_error ? (refused ? "refused" : "error") : s.kind;
    const label = `${KIND_LABELS[s.kind] || s.kind}${s.tool ? ` <code>${Format.esc(s.tool)}</code>` : ""}`;
    let content = Format.esc(s.content);

    if (s.kind === "tool_call") {
      try { content = Format.esc(JSON.stringify(JSON.parse(s.content), null, 2)); } catch {}
      content = `<pre class="trace__code">${content}</pre>`;
    } else if (s.kind === "prompt" || (s.kind === "tool_result" && s.content.length > 400)) {
      content = `<details><summary>${s.kind === "prompt" ? "ver contexto completo enviado ao modelo" : `ver resposta completa (${Format.number.format(s.content.length)} caracteres)`}</summary><pre class="trace__code">${content}</pre></details>`;
    } else {
      content = `<p class="trace__text">${content}</p>`;
    }

    return `<li class="trace__step trace__step--${tone}">
      <span class="trace__kind">${label}${refused ? " " + Html.badge("recusado pela trava", "warning") : s.is_error ? " " + Html.badge("erro", "danger") : ""}</span>
      <span class="trace__time">${Format.short(s.created_at)}</span>
      ${content}
    </li>`;
  }
}

class FeedPanel {
  constructor() {
    this.root = document.getElementById("feed");
    this.includeLogs = document.getElementById("feed-logs");
    document.getElementById("feed-clear").addEventListener("click", () => { this.root.innerHTML = ""; });
    this.count = 0;
  }

  push(event, data) {
    if (event === "log" && !this.includeLogs.checked) return;
    if (this.count === 0) this.root.innerHTML = "";
    this.count += 1;

    const item = document.createElement("li");
    item.className = `feed__item feed__item--${event}${data.is_error ? " is-error" : ""}`;
    item.innerHTML = this.describe(event, data);
    this.root.prepend(item);

    while (this.root.children.length > 200) this.root.lastElementChild.remove();
  }

  describe(event, d) {
    const time = `<span class="feed__time">${Format.short(d.at)}</span>`;
    if (event === "run_started") return `${time}<b>Rodada ${Format.esc(d.run_id)} começou</b> <span class="muted">${TRIGGERS[d.trigger] || d.trigger} · ${d.brain === "llm" ? Format.esc(d.model) : "regras"}${d.dry_run ? " · simulação" : ""}</span>`;
    if (event === "run_finished") return `${time}<b>Rodada ${Format.esc(d.run_id)} ${d.status === "failed" ? "falhou" : "terminou"}</b> <span class="muted">${d.actions_ok} feitas · ${d.actions_refused} recusadas · ${d.actions_failed} falhas</span>`;
    if (event === "log") return `${time}${Html.badge(Format.esc(d.level.toLowerCase()), d.level === "ERROR" ? "danger" : d.level === "WARNING" ? "warning" : "neutral")} ${Format.esc(d.message)}`;
    const meta = Format.agent(d.agent);
    const text = d.content.length > 220 ? `${d.content.slice(0, 219)}…` : d.content;
    return `${time}<span class="feed__agent" style="--agent-color: var(--series-${meta.slot})"><span class="agent-card__swatch" aria-hidden="true"></span>${meta.label}</span> <span class="muted">${KIND_LABELS[d.kind] || d.kind}${d.tool ? ` ${Format.esc(d.tool)}` : ""}</span> ${Format.esc(text)}`;
  }
}


class PlanPanel {
  static KINDS = { build: "construir", recruit: "recrutar", unlock_scavenge: "desbloquear coleta" };
  static STATES = { pending: ["pendente", "neutral"], queued: ["em andamento", "info"], done: ["feito", "success"], blocked: ["bloqueado", "warning"] };
  static TARGETS = {
    main: "Edifício principal", barracks: "Quartel", stable: "Estábulo", garage: "Oficina", smith: "Ferreiro", snob: "Academia",
    market: "Mercado", place: "Praça de reunião", statue: "Estátua", watchtower: "Torre de vigia", wood: "Bosque", stone: "Poço de argila",
    iron: "Mina de ferro", farm: "Fazenda", storage: "Armazém", hide: "Esconderijo", wall: "Muralha",
    spear: "Lanceiro", sword: "Espadachim", axe: "Bárbaro", archer: "Arqueiro", spy: "Explorador", light: "Cavalaria leve",
    marcher: "Arqueiro a cavalo", heavy: "Cavalaria pesada", ram: "Aríete", catapult: "Catapulta", knight: "Paladino",
  };

  constructor(api) {
    this.api = api;
    this.root = document.getElementById("plans");
  }

  label(step) {
    const target = PlanPanel.TARGETS[step.target] || (step.kind === "unlock_scavenge" ? `nível ${step.target}` : step.target);
    if (step.kind === "build") return `${PlanPanel.KINDS.build} ${target} até o nível ${step.amount}`;
    if (step.kind === "recruit") return `${PlanPanel.KINDS.recruit} ${target} até ${Format.number.format(step.amount)}`;
    return `${PlanPanel.KINDS.unlock_scavenge} ${target}`;
  }

  async load() {
    let plans = [];
    try {
      plans = await this.api.get("/agents/plans");
    } catch {
      return;
    }

    if (!plans.length || plans.every((p) => !p.total)) {
      this.root.innerHTML = '<p class="empty">Ainda não há plano. O Estrategista cria um na próxima rodada.</p>';
      return;
    }

    this.root.innerHTML = plans.map((p) => {
      const pct = p.total ? Math.round((p.done / p.total) * 100) : 0;
      const source = p.source === "llm" ? "IA" : p.source === "rules" ? "regras" : p.source;
      return `<article class="plan">
        <header class="plan__head">
          <b>${Format.esc(p.village)}</b>
          <span class="muted">feito por ${source} · ${p.refreshed_at ? `atualizado ${Format.relative(p.refreshed_at)}` : "—"}</span>
          <span class="plan__progress">${p.done}/${p.total} passos</span>
        </header>
        <div class="meter" aria-hidden="true"><i style="width:${pct}%; --meter-color: var(--color-success)"></i></div>
        ${p.summary ? `<p class="plan__summary">${Format.esc(p.summary)}</p>` : ""}
        <ol class="plan__steps">${p.steps.map((s) => {
          const [text, tone] = PlanPanel.STATES[s.status] || [s.status, "neutral"];
          return `<li class="plan__step plan__step--${s.status}"><span>${this.label(s)}${s.reason ? `<small class="muted"> — ${Format.esc(s.reason)}</small>` : ""}</span>
            <span class="plan__state">${Html.badge(text, tone)}${s.note ? `<small class="muted">${Format.esc(s.note)}</small>` : ""}</span></li>`;
        }).join("")}</ol>
      </article>`;
    }).join("");
  }
}

class AgentsPage {
  constructor() {
    this.api = new Api();
    this.toast = new Toast();
    this.live = new LivePanel(this.api);
    this.cards = new AgentCards();
    this.trace = new TracePanel(this.api);
    this.runs = new RunsPanel(this.api, this.trace);
    this.feed = new FeedPanel();
    this.plans = new PlanPanel(this.api);
    this.events = new EventFeed();
  }

  async start() {
    this.bindRunButtons();
    await this.refresh();

    const params = new URLSearchParams(location.search);
    if (params.get("run")) this.trace.load(params.get("run"));

    this.events.on((kind, data) => this.onEvent(kind, data)).connect();
    setInterval(() => this.live.load(), 5000);
    setInterval(() => this.refresh(), 30000);
  }

  async refresh() {
    const [config, stats] = await Promise.all([
      this.api.get("/agents/config").catch(() => null),
      this.api.get("/agents/stats?hours=24").catch(() => null),
      this.live.load(),
      this.runs.load(),
      this.plans.load(),
    ]);

    if (config) this.live.setBrain(config);
    this.cards.render(stats, config);
  }

  onEvent(kind, data) {
    this.feed.push(kind, data);
    if (kind === "log") return;

    this.live.apply(kind, data);
    if (kind === "step") this.trace.append(data);
    if (kind === "run_started") this.runs.load();
    if (kind === "run_finished") this.refresh();
  }

  bindRunButtons() {
    const run = (dryRun) => async (e) => {
      const button = e.currentTarget;
      if (!dryRun && !confirm("Rodar os agentes no jogo agora? Eles podem construir, recrutar, coletar e saquear bárbaras.")) return;

      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      this.toast.show(dryRun ? "Simulando rodada… acompanhe ao vivo" : "Rodada em andamento… acompanhe ao vivo");

      try {
        const report = await this.api.send("/agents/run", "POST", { dry_run: dryRun });
        if (report.error) this.toast.show(report.error, true);
        else {
          this.toast.show(`Rodada ${report.run_id} concluída`);
          this.trace.load(report.run_id);
        }
      } catch (err) {
        this.toast.show(err.message, true);
      } finally {
        button.disabled = false;
        button.removeAttribute("aria-busy");
        this.refresh();
      }
    };

    document.getElementById("btn-sim").addEventListener("click", run(true));
    document.getElementById("btn-live").addEventListener("click", run(false));
  }
}

new AgentsPage().start();
