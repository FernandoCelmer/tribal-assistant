import { Busy, Countdown, Format, Html, Page, VillagePicker } from "/static/js/core.js";

const PRIORITY = { high: "alta", medium: "média", low: "baixa" };
const PRIORITY_TONES = { high: "danger", medium: "warning", low: "neutral" };
const COMMAND_KINDS = { attack: "ataque", noble: "nobre", support: "apoio", return: "retorno", cancel: "cancelado", other: "outro" };
const QUEST_STATES = { progress: "em andamento", new: "nova", finished: "concluída" };

class OverviewPage extends Page {
  constructor() {
    super({ every: 10000 });
    this.overview = null;
    this.picker = new VillagePicker(document.getElementById("village-select"));
    this.picker.onChange(() => this.renderVillage());
    this.bindButtons();
    setInterval(() => this.renderResources(), 1000);
    Countdown.start();
  }

  $(id) {
    return document.getElementById(id);
  }

  async refresh() {
    await Promise.all([this.loadStatus(), this.loadOverview(), this.loadQuests()]);
  }

  async loadStatus() {
    try {
      const h = await this.api.get("/health");
      this.$("s-health").innerHTML = Html.pill(true, `ok v${Format.esc(h.version)}`, "", "check");
    } catch {
      this.$("s-health").innerHTML = Html.pill(false, "", "offline", "", "alert");
    }

    try {
      const s = await this.api.get("/assistant/status");
      this.$("s-running").innerHTML = Html.pill(s.running, "rodando", "parado", "refresh", "stop");
      this.$("s-login").innerHTML = Html.pill(s.logged_in, "logado", "deslogado", "pop", "key");
      this.$("s-world").textContent = s.world || "—";
      this.$("s-sync").textContent = Format.when(s.last_sync_at);
      this.$("s-error").hidden = !s.last_error;
      this.$("s-error-text").textContent = s.last_error || "";
    } catch {
      this.$("s-running").textContent = "erro";
    }
  }

  async loadOverview() {
    try {
      this.overview = await this.api.get("/game/overview");
    } catch {
      return;
    }
    this.picker.update(this.overview.villages);
    this.renderPlayer();
    this.renderVillage();
    this.renderCommands();
  }

  renderPlayer() {
    const p = this.overview?.player;
    if (!p) {
      this.$("player").innerHTML = `<p class="empty">Sem dados do jogador ainda.</p>`;
      return;
    }

    const extras = [];
    if (p.protection_until && Format.date(p.protection_until) > Date.now()) extras.push(Html.badge(`${Html.icon("shield")}Proteção <span data-until="${Format.esc(p.protection_until)}"></span>`, "info"));
    if (p.new_reports) extras.push(Html.badge(`${p.new_reports} relatório(s) novo(s)`, "warning"));
    if (p.new_mails) extras.push(Html.badge(`${p.new_mails} mensagem(ns)`, "warning"));
    if (p.daily_bonus) extras.push(Html.badge("bônus diário disponível", "success"));
    if (p.new_quests) extras.push(Html.badge("missão nova", "neutral"));

    const row = (icon, label, value) => `<div>${Html.icon(icon)}<dt>${label}</dt><dd>${value}</dd></div>`;
    this.$("player").innerHTML = `
      <p class="account__name">${Format.esc(p.name)}</p>
      <dl class="ledger">
        ${row("star", "Pontos", Format.number.format(p.points))}
        ${row("trophy", "Ranking", `#${Format.number.format(p.rank)}`)}
        ${row("castle", "Aldeias", p.villages)}
        ${row("gem", "Pontos premium", Format.number.format(p.premium_points))}
        ${row("swords", "Ataques chegando", p.incomings ? Html.badge(`${Html.icon("swords")}${p.incomings}`, "danger") : "0")}
      </dl>
      ${extras.length ? `<div class="badge-row panel__foot-badges">${extras.join("")}</div>` : ""}`;
  }

  liveStock(v, key) {
    const hours = v.synced_at ? (Date.now() - Format.date(v.synced_at)) / 3.6e6 : 0;
    return Math.min(v.storage, Math.floor(v[key] + v[`${key}_prod`] * hours));
  }

  renderResources() {
    const v = this.picker.current();
    if (!v) return;

    for (const key of ["wood", "clay", "iron"]) {
      const stock = this.liveStock(v, key);
      const prod = v[`${key}_prod`];
      const full = prod > 0 && stock < v.storage ? ` · cheio em ${Format.duration(((v.storage - stock) / prod) * 3600)}` : stock >= v.storage ? " · CHEIO" : "";
      this.$(`r-${key}`).textContent = Format.number.format(stock);
      this.$(`r-${key}-sub`).textContent = `+${Format.number.format(prod)}/h${full}`;
      this.$(`r-${key}-bar`).style.width = `${v.storage ? (stock / v.storage) * 100 : 0}%`;
    }

    const pop = v.pop_max ? (v.pop_current / v.pop_max) * 100 : 0;
    this.$("r-storage").textContent = Format.number.format(v.storage);
    this.$("r-storage-sub").textContent = "capacidade por recurso";
    this.$("r-pop").textContent = `${Format.number.format(v.pop_current)} / ${Format.number.format(v.pop_max)}`;
    this.$("r-pop-sub").textContent = `${Format.number.format(v.pop_max - v.pop_current)} livres`;
    this.$("r-pop-bar").style.width = `${pop}%`;
    this.$("r-pop-bar").style.background = pop >= 85 ? "var(--color-danger)" : "var(--color-text-muted)";
  }

  recStatus(r) {
    if (r.can_build) return Html.badge("pode construir agora", "success");
    if (r.blocker && r.eta_seconds === 0) return Html.badge(Format.esc(r.blocker));
    if (r.eta_seconds != null) return Html.badge(`recursos em ${Format.duration(r.eta_seconds)}`, "warning");
    return Html.badge(Format.esc(r.blocker || "armazém insuficiente"));
  }

  renderVillage() {
    const v = this.picker.current();
    this.$("village-empty").hidden = !!v;
    for (const id of ["village-body", "village-detail"]) this.$(id).hidden = !v;
    if (!v) {
      this.$("v-meta").textContent = "";
      return;
    }

    this.$("v-meta").textContent = `${v.name} · ${v.coords} · ${Format.number.format(v.points)} pontos · sync ${Format.when(v.synced_at)}`;
    this.renderResources();

    this.$("recs").innerHTML = v.recommendations.length ? v.recommendations.map((r) => `
      <li class="rec inset">
        <div class="rec__top"><b>${Format.esc(r.label)} ${r.from_level} → ${r.to_level}</b>
          ${Html.badge(PRIORITY[r.priority] || Format.esc(r.priority), PRIORITY_TONES[r.priority])}${this.recStatus(r)}</div>
        <div class="rec__cost">
          <span class="res res--wood">${Html.icon("wood")}${Format.number.format(r.wood)}</span>
          <span class="res res--clay">${Html.icon("clay")}${Format.number.format(r.clay)}</span>
          <span class="res res--iron">${Html.icon("iron")}${Format.number.format(r.iron)}</span>
          <span class="muted">pop ${r.pop} · ${Format.duration(r.build_time)}</span></div>
        <p class="rec__why">${Format.esc(r.reason)}</p>
      </li>`).join("") : `<li class="empty">Nada urgente.</li>`;

    this.$("scavenge").innerHTML = v.scavenge.length ? v.scavenge.map((o) => {
      const state = o.is_locked
        ? (o.unlock_at ? `desbloqueando <span data-until="${Format.esc(o.unlock_at)}"></span>` : "bloqueada")
        : o.return_at ? `volta em <span data-until="${Format.esc(o.return_at)}"></span>` : Html.badge("livre", "success");
      return `<li class="tile inset ${o.is_locked && !o.unlock_at ? "is-dim" : ""}"><span><b>${Format.esc(o.name)}</b><br><span class="muted">${Math.round(o.loot_factor * 100)}% do carregamento</span></span><span class="tile__state">${state}</span></li>`;
    }).join("") : `<li class="empty">Sem dados de coleta.</li>`;

    Countdown.tick();
  }

  renderCommands() {
    const list = this.overview?.commands || [];
    const incoming = list.filter((c) => c.direction === "in" && (c.kind === "attack" || c.kind === "noble"));
    const card = this.$("commands-card");
    card.hidden = !list.length;
    card.classList.toggle("is-alert", incoming.length > 0);
    this.$("inc-count").hidden = !incoming.length;
    this.$("inc-count").textContent = `${incoming.length} ataque(s) chegando`;

    this.$("commands").innerHTML = list.map((c) => {
      const danger = c.direction === "in" && (c.kind === "attack" || c.kind === "noble");
      const tone = danger ? "danger" : c.direction === "in" ? "warning" : "neutral";
      return `<tr>
        <td>${Html.badge(`${c.direction === "in" ? "chegando" : "saindo"} · ${COMMAND_KINDS[c.kind] || Format.esc(c.kind)}`, tone)}</td>
        <td>${Format.esc(c.village_coords)}</td><td>${Format.esc(c.label)}</td><td>${Format.when(c.arrival_at)}</td>
        <td class="num" data-until="${Format.esc(c.arrival_at)}"></td></tr>`;
    }).join("");
    Countdown.tick();
  }

  async loadQuests() {
    let data;
    try {
      data = await this.api.get("/agents/quests");
    } catch {
      return;
    }

    this.$("quests-meta").textContent = data.rewards.length ? `${data.rewards.length} recompensa(s) para coletar` : "";
    this.$("quests").innerHTML = data.quests.length ? data.quests.map((q) => `
      <li class="rec inset">
        <div class="rec__top"><b>${Format.esc(q.title)}</b>${q.can_complete ? Html.badge("pronta", "success") : Html.badge(Format.esc(QUEST_STATES[q.state] || q.state))}</div>
        ${q.goals.map((g) => `<div class="rec__cost"><span>${Format.esc(g.title)}</span>${g.target != null ? `<span class="muted">${g.current}/${g.target}</span>` : ""}</div>`).join("")}
      </li>`).join("") : `<li class="empty">Missões aparecem após a primeira rodada dos agentes.</li>`;
  }

  bindButtons() {
    const after = () => this.tick();

    this.$("btn-sync").addEventListener("click", (e) => Busy.run(e.currentTarget, async () => {
      this.toast.show("Sincronizando… se aparecer captcha, resolva na janela do Chromium");
      const r = await this.api.send("/assistant/sync");
      this.toast.show(r.message, !r.ok);
    }, after));

    this.$("btn-start").addEventListener("click", (e) => Busy.run(e.currentTarget, async () => {
      this.toast.show((await this.api.send("/assistant/start")).message);
    }, after));

    this.$("btn-stop").addEventListener("click", (e) => Busy.run(e.currentTarget, async () => {
      this.toast.show((await this.api.send("/assistant/stop")).message);
    }, after));
  }
}

new OverviewPage().start();
