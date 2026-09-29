export const API = "/api/v1";

export const AGENTS = [
  { key: "quartermaster", label: "Missões", slot: 1, area: "missões e recompensas" },
  { key: "strategist", label: "Estrategista", slot: 2, area: "objetivo da aldeia" },
  { key: "economist", label: "Economista", slot: 3, area: "recursos, armazém, fazenda, mercado, coleta" },
  { key: "commander", label: "Comandante", slot: 4, area: "militar e recrutamento" },
  { key: "raider", label: "Saqueador", slot: 5, area: "saque de bárbaras e coleta" },
  { key: "operator", label: "Operador", slot: 6, area: "ordens diretas (MCP)" },
];

export const UNIT_LABELS = {
  spear: "Lanceiro", sword: "Espadachim", axe: "Bárbaro", archer: "Arqueiro", spy: "Explorador",
  light: "Cavalaria leve", marcher: "Arqueiro a cavalo", heavy: "Cavalaria pesada", ram: "Aríete",
  catapult: "Catapulta", knight: "Paladino", snob: "Nobre", militia: "Milícia",
};

export class Format {
  static number = new Intl.NumberFormat("pt-BR");

  static esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  static date(iso) {
    if (!iso) return null;
    return new Date(/Z|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
  }

  static when(iso) {
    const d = Format.date(iso);
    return d ? d.toLocaleString("pt-BR") : "—";
  }

  static short(iso) {
    const d = Format.date(iso);
    return d ? d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "—";
  }

  static duration(seconds) {
    if (seconds == null) return "—";
    const s = Math.max(0, Math.round(seconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h) return `${h}h ${String(m).padStart(2, "0")}m`;
    if (m) return `${m}m ${String(s % 60).padStart(2, "0")}s`;
    return `${s}s`;
  }

  static relative(iso) {
    const d = Format.date(iso);
    if (!d) return "—";
    const diff = (d - Date.now()) / 1000;
    return diff >= 0 ? `em ${Format.duration(diff)}` : `há ${Format.duration(-diff)}`;
  }

  static agent(key) {
    return AGENTS.find((a) => a.key === key) || { key, label: key, slot: 6, area: "" };
  }
}

export class Html {
  static icon(name, cls = "") {
    return `<svg class="icon ${cls}" aria-hidden="true"><use href="/static/icons.svg#i-${name}"/></svg>`;
  }

  static badge(html, tone = "neutral") {
    return `<span class="badge badge--${tone}">${html}</span>`;
  }

  static pill(on, yes, no, onIcon = "", offIcon = "") {
    const icon = on ? (onIcon && Html.icon(onIcon)) : (offIcon && Html.icon(offIcon));
    return Html.badge(`${icon}${on ? yes : no}`, on ? "success" : "danger");
  }

  static empty(colspan, text) {
    return `<tr><td colspan="${colspan}" class="empty">${text}</td></tr>`;
  }
}

export class Api {
  static errorText(body, status) {
    const d = body && body.detail;
    if (!d) return `HTTP ${status}`;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((e) => e.msg).join("; ");
    return d.message || JSON.stringify(d);
  }

  async request(path, options = {}) {
    const url = path.startsWith("/api") || path.startsWith("/health") ? path : `${API}${path}`;
    const res = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new Error(Api.errorText(body, res.status));
    return body;
  }

  get(path) {
    return this.request(path);
  }

  send(path, method = "POST", body = undefined) {
    return this.request(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
  }
}

export class Toast {
  constructor(node = document.getElementById("toast")) {
    this.node = node;
    this.timer = null;
  }

  show(message, error = false) {
    if (!this.node) return;
    this.node.className = `toast alert alert--${error ? "danger" : "info"} is-shown`;
    this.node.innerHTML = `${Html.icon(error ? "alert" : "info", "alert__icon")}<span>${Format.esc(message)}</span>`;
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.node.classList.remove("is-shown"), 4500);
  }
}

export class Busy {
  static async run(button, fn, after) {
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    try {
      await fn();
    } catch (err) {
      new Toast().show(err.message, true);
    } finally {
      button.disabled = false;
      button.removeAttribute("aria-busy");
      if (after) after();
    }
  }
}

export class Theme {
  static color(slot) {
    return getComputedStyle(document.documentElement).getPropertyValue(`--series-${slot}`).trim() || "#888";
  }

  static token(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  static onChange(fn) {
    new MutationObserver(fn).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", fn);
  }
}

export class Countdown {
  static tick() {
    for (const el of document.querySelectorAll("[data-until]")) {
      const until = el.dataset.until;
      el.textContent = until ? Format.duration((Format.date(until) - Date.now()) / 1000) : "";
    }
  }

  static start() {
    setInterval(Countdown.tick, 1000);
  }
}

export class VillagePicker {
  static KEY = "tw.village";

  constructor(select) {
    this.select = select;
    this.villages = [];
    this.listeners = [];
    try {
      this.selected = Number(localStorage.getItem(VillagePicker.KEY)) || null;
    } catch {
      this.selected = null;
    }
    this.select?.addEventListener("change", () => {
      this.selected = Number(this.select.value);
      try { localStorage.setItem(VillagePicker.KEY, this.selected); } catch {}
      this.listeners.forEach((fn) => fn(this.current()));
    });
  }

  onChange(fn) {
    this.listeners.push(fn);
  }

  update(villages) {
    this.villages = villages || [];
    if (!this.select) return;
    this.select.hidden = this.villages.length < 2;
    this.select.innerHTML = this.villages.map((v) => `<option value="${v.id}">${Format.esc(v.name)} (${Format.esc(v.coords)})</option>`).join("");
    const v = this.current();
    if (v) this.select.value = v.id;
  }

  current() {
    return this.villages.find((v) => v.id === this.selected) || this.villages[0] || null;
  }
}

export class EventFeed {
  static KINDS = ["run_started", "step", "run_finished", "log"];

  constructor(statusNode = document.getElementById("stream-status")) {
    this.status = statusNode;
    this.handlers = [];
    this.source = null;
  }

  on(fn) {
    this.handlers.push(fn);
    return this;
  }

  connect() {
    this.source = new EventSource(`${API}/events`);
    this.source.onopen = () => this.setStatus("ao vivo", "on");
    this.source.onerror = () => this.setStatus("reconectando…", "off");

    for (const kind of EventFeed.KINDS) {
      this.source.addEventListener(kind, (e) => {
        const data = JSON.parse(e.data);
        this.handlers.forEach((fn) => fn(kind, data));
      });
    }
    return this;
  }

  setStatus(text, state) {
    if (!this.status) return;
    this.status.hidden = false;
    this.status.textContent = text;
    this.status.dataset.state = state;
  }
}

export class Page {
  constructor({ every = 15000 } = {}) {
    this.api = new Api();
    this.toast = new Toast();
    this.every = every;
    this.updated = document.getElementById("updated");
  }

  async refresh() {}

  async tick() {
    await this.refresh();
    if (this.updated) this.updated.textContent = `atualizado ${new Date().toLocaleTimeString("pt-BR")}`;
  }

  async start() {
    await this.tick();
    if (this.every) setInterval(() => this.tick(), this.every);
    return this;
  }
}
