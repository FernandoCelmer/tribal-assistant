import { Api, EventFeed, Format, Html } from "/static/js/core.js";

class LogsPanel {
  static LEVELS = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"];

  constructor(api) {
    this.api = api;
    this.body = document.getElementById("logs-body");
    this.level = document.getElementById("log-level");
    this.search = document.getElementById("log-search");
    this.tail = document.getElementById("log-tail");
    this.oldest = null;
    this.level.addEventListener("change", () => this.load());
    let timer;
    this.search.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => this.load(), 300); });
    document.getElementById("logs-more").addEventListener("click", () => this.load(true));
  }

  row(l) {
    const tone = { ERROR: "danger", CRITICAL: "danger", WARNING: "warning", SUCCESS: "success" }[l.level] || "neutral";
    return `<tr><td class="muted">${Format.short(l.at)}</td><td>${Html.badge(l.level.toLowerCase(), tone)}</td><td class="log__message">${Format.esc(l.message)}</td><td class="muted log__source">${Format.esc(l.source)} <span class="log__process">${Format.esc(l.process)}</span></td></tr>`;
  }

  async load(older = false) {
    const params = new URLSearchParams({ level: this.level.value, limit: "150" });
    if (this.search.value.trim()) params.set("q", this.search.value.trim());
    if (older && this.oldest) params.set("before_id", this.oldest);

    let rows = [];
    try {
      rows = await this.api.get(`/logs?${params}`);
    } catch {
      return;
    }

    if (rows.length) this.oldest = rows[rows.length - 1].id;
    const html = rows.map((l) => this.row(l)).join("");
    if (older) this.body.insertAdjacentHTML("beforeend", html);
    else this.body.innerHTML = html || '<tr><td colspan="4" class="empty">Nenhum log com esses filtros.</td></tr>';
  }

  live(data) {
    if (!this.tail.checked) return;
    if (LogsPanel.LEVELS.indexOf(data.level) < LogsPanel.LEVELS.indexOf(this.level.value)) return;
    const q = this.search.value.trim().toLowerCase();
    if (q && !data.message.toLowerCase().includes(q)) return;
    this.body.querySelector(".empty")?.closest("tr")?.remove();
    this.body.insertAdjacentHTML("afterbegin", this.row(data));
    while (this.body.children.length > 500) this.body.lastElementChild.remove();
  }
}

class LogsPage {
  constructor() {
    this.logs = new LogsPanel(new Api());
    this.events = new EventFeed();
  }

  async start() {
    await this.logs.load();
    this.events.on((kind, data) => { if (kind === "log") this.logs.live(data); }).connect();
  }
}

new LogsPage().start();
