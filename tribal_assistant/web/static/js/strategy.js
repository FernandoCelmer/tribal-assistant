import { Format, Html, Page } from "/static/js/core.js";

const ROLES = { growth: "Crescimento", defense: "Defesa", offensive: "Ofensiva", support: "Apoio", expansion: "Expansão", emergency: "Emergência" };
const CERTAINTY = { fact: ["fato", "success"], estimate: ["estimativa", "info"], hypothesis: ["hipótese", "warning"] };
const HORIZON = { immediate: "imediato", tactical: "tático", strategic: "estratégico" };
const RES = { wood: "madeira", clay: "argila", stone: "argila", iron: "ferro", pop: "pop" };

class StrategyPage extends Page {
  constructor() {
    super({ every: 20000 });
    this.select = document.getElementById("strategy-village");
    this.rounds = [];
    this.proposers = {};
    this.selected = null;
    this.select.addEventListener("change", () => { this.selected = Number(this.select.value); this.render(); });
  }

  async refresh() {
    const [rounds, proposers] = await Promise.all([this.api.get("/agents/coordination"), this.api.get("/agents/proposers")]);
    this.rounds = rounds;
    this.proposers = Object.fromEntries(proposers.map((p) => [p.key, p]));
    this.select.hidden = rounds.length < 2;
    this.select.innerHTML = rounds.map((r) => `<option value="${r.village_id}">${Format.esc(r.village)}</option>`).join("");
    if (!rounds.find((r) => r.village_id === this.selected)) this.selected = rounds[0]?.village_id ?? null;
    if (this.selected != null) this.select.value = this.selected;
    this.renderTeam(proposers);
    this.render();
  }

  current() {
    return this.rounds.find((r) => r.village_id === this.selected);
  }

  who(key) {
    return this.proposers[key]?.title || key;
  }

  static cost(cost) {
    const parts = Object.entries(cost || {}).filter(([, v]) => v).map(([k, v]) => `${Format.number.format(v)} ${RES[k] || k}`);
    return parts.join(" · ") || "sem custo";
  }

  render() {
    const round = this.current();
    const head = document.getElementById("strategy-head");
    if (!round) {
      head.innerHTML = `<p class="empty">Nenhuma rodada do coordenador ainda. Rode os agentes em Agentes.</p>`;
      return;
    }

    const d = round.data;
    const roleSelect = `<select class="select" id="role-select" aria-label="Papel da aldeia">
      <option value="">automático (${ROLES[d.role] || d.role})</option>
      ${["growth", "defense", "offensive", "support", "expansion"].map((r) => `<option value="${r}" ${round.manual_role && d.role === r ? "selected" : ""}>${ROLES[r]}</option>`).join("")}
    </select>`;

    head.innerHTML = `
      <div class="kpis">
        <div class="kpi"><span class="kpi__label">Papel</span><span class="kpi__value">${ROLES[d.role] || d.role}</span><span class="kpi__sub">${round.manual_role ? "escolhido por você" : "escolhido pelo coordenador"}</span></div>
        <div class="kpi"><span class="kpi__label">Modo desta rodada</span><span class="kpi__value">${ROLES[d.mode] || d.mode}</span><span class="kpi__sub">${Format.esc(d.goal)}</span></div>
        <div class="kpi"><span class="kpi__label">Próxima reavaliação</span><span class="kpi__value">${Format.relative(round.next_review_at)}</span><span class="kpi__sub">rodada ${Format.short(round.created_at)}</span></div>
      </div>
      <div class="form-row"><label class="field__label" for="role-select">Fixar papel</label>${roleSelect}</div>`;

    document.getElementById("role-select").addEventListener("change", (e) => this.setRole(e.target.value));

    const next = d.next_action;
    document.getElementById("strategy-next").innerHTML = next ? `
      <strong class="display">${Format.esc(next.title)}</strong>
      <p><b>Por quê:</b> ${Format.esc(next.reason)}</p>
      ${next.expected_benefit ? `<p><b>Impacto:</b> ${Format.esc(next.expected_benefit)}</p>` : ""}
      <p><b>Custo:</b> ${StrategyPage.cost(next.cost)} · <b>Confiança:</b> ${Math.round((next.confidence || 0) * 100)}% · <b>Prioridade:</b> ${next.priority}</p>
      ${next.why ? `<p class="muted">Adiada: ${Format.esc(next.why)}</p>` : `<p class="muted">${Format.esc(next.result || "")}</p>`}
      ${next.risks?.length ? `<p class="muted">Riscos: ${next.risks.map(Format.esc).join("; ")}</p>` : ""}` : `<p class="empty">Nada a fazer nesta rodada.</p>`;

    const budget = d.budget || {};
    const reservations = (budget.reservations || []).map((r) => `<li><b>${Format.esc(r.purpose)}</b> (${Format.esc(r.kind)}): ${StrategyPage.cost(r.cost)}${Object.keys(r.troops || {}).length ? ` · tropas ${Object.entries(r.troops).map(([u, n]) => `${n} ${u}`).join(", ")}` : ""}<br><span class="muted">${Format.esc(r.reason)}</span></li>`).join("");
    const vetoes = (d.constraints || []).map((c) => `<li>${Html.badge("veto", "danger")} ${Format.esc(c.reason)}${c.until ? ` <span class="muted">até ${Format.short(c.until)}</span>` : ""}</li>`).join("");
    document.getElementById("strategy-budget").innerHTML = `
      <p><b>Livre para gastar:</b> ${StrategyPage.cost(budget.free)}</p>
      <p class="muted">Estoque ${StrategyPage.cost(budget.stock)} · reservado ${StrategyPage.cost(budget.held)}</p>
      <ul class="stack">${reservations || "<li class='muted'>sem reservas</li>"}</ul>
      <ul class="stack">${vetoes || "<li class='muted'>sem vetos ativos</li>"}</ul>`;

    document.getElementById("strategy-executed").innerHTML = (d.executed || []).map((e) => `<tr>
      <td class="num">${e.priority}</td><td>${Format.esc(e.title)}</td><td>${Format.esc(this.who(e.source))}</td>
      <td>${Format.esc(e.reason)}</td><td class="num">${Math.round(e.confidence * 100)}%</td>
      <td>${Html.badge(Format.esc(e.result || ""), e.ok ? "success" : "danger")}</td></tr>`).join("") || Html.empty(6, "Nada executado nesta rodada.");

    document.getElementById("strategy-deferred").innerHTML = (d.deferred || []).map((e, i) => `<tr>
      <td class="num">${e.priority}</td><td>${Format.esc(e.title)}</td><td>${Format.esc(this.who(e.source))}</td>
      <td>${Format.esc(e.why)}</td><td>${HORIZON[e.horizon] || e.horizon}</td>
      <td class="num">${e.ready_in_hours != null ? Format.duration(e.ready_in_hours * 3600) : "—"}</td>
      <td>${e.why === "aguardando aprovação do jogador" ? `<button class="btn btn--sm btn--primary" data-approve="${i}">Aprovar</button>` : ""}</td></tr>`).join("") || Html.empty(7, "Nenhuma proposta adiada.");

    for (const btn of document.querySelectorAll("[data-approve]")) {
      btn.addEventListener("click", () => this.approve(d.deferred[Number(btn.dataset.approve)], btn));
    }

    document.getElementById("strategy-insights").innerHTML = (d.insights || []).map((i) => {
      const [label, tone] = CERTAINTY[i.certainty] || [i.certainty, "neutral"];
      return `<tr><td>${Html.badge(label, tone)}</td><td>${Format.esc(i.text)}</td><td class="num">${Format.duration(i.age_hours * 3600)}</td><td class="num">${Math.round(i.weight * 100)}%</td></tr>`;
    }).join("") || Html.empty(4, "Sem informações.");
  }

  renderTeam(proposers) {
    document.getElementById("strategy-team").innerHTML = proposers.map((p) => `<tr><td><b>${Format.esc(p.title)}</b></td><td>${Format.esc(p.observes)}</td><td>${Format.esc(p.delivers)}</td></tr>`).join("");
  }

  async setRole(role) {
    try {
      await this.api.send(`/agents/villages/${this.selected}/role`, "PUT", { role: role || null, reason: role ? "escolhido no painel" : "" });
      this.toast.show(role ? `Papel fixado: ${ROLES[role]}` : "Papel volta a ser automático");
      await this.refresh();
    } catch (err) {
      this.toast.show(err.message, true);
    }
  }

  async approve(entry, btn) {
    btn.disabled = true;
    try {
      const out = await this.api.send("/agents/act", "POST", { village_id: this.selected, tool: entry.action, arguments: { ...entry.arguments, reason: "aprovado no painel" }, dry_run: false });
      this.toast.show(out.detail, !out.ok);
    } catch (err) {
      this.toast.show(err.message, true);
    } finally {
      btn.disabled = false;
    }
  }
}

new StrategyPage().start();
