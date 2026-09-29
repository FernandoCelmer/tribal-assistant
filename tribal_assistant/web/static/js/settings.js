import { Api, Format, Html, Toast } from "/static/js/core.js";

class SettingsPage {
  constructor() {
    this.api = new Api();
    this.toast = new Toast();
    this.form = document.getElementById("agent-settings");
    this.state = document.getElementById("settings-state");
    this.saved = null;
  }

  async start() {
    this.form.addEventListener("submit", (e) => this.save(e));
    this.form.addEventListener("input", () => this.markDirty());
    this.form.addEventListener("reset", (e) => {
      e.preventDefault();
      if (this.saved) this.fill(this.saved);
      this.markDirty();
    });

    await Promise.all([this.loadSettings(), this.loadSystem()]);
  }

  async loadSettings() {
    try {
      this.saved = await this.api.get("/agents/settings");
    } catch (err) {
      this.toast.show(err.message, true);
      return;
    }
    this.fill(this.saved);
    this.markDirty();
  }

  fill(settings) {
    for (const [key, value] of Object.entries(settings)) {
      if (Array.isArray(value)) {
        this.form.querySelectorAll(`input[name="${key}"]`).forEach((box) => { box.checked = value.includes(box.value); });
        continue;
      }
      const input = this.form.elements[key];
      if (!input) continue;
      if (input.type === "checkbox") input.checked = !!value;
      else input.value = input.hasAttribute("data-percent") ? Math.round(value * 100) : value;
    }
  }

  read() {
    const lists = ["llm_agents", "approval_actions"];
    const body = Object.fromEntries(lists.map((name) => [name, [...this.form.querySelectorAll(`input[name="${name}"]:checked`)].map((b) => b.value)]));
    for (const input of this.form.querySelectorAll("input[name]")) {
      if (lists.includes(input.name)) continue;
      if (input.type === "checkbox") body[input.name] = input.checked;
      else if (input.value !== "") body[input.name] = input.hasAttribute("data-percent") ? Number(input.value) / 100 : Number(input.value);
    }
    return body;
  }

  markDirty() {
    if (!this.saved) return;
    const current = this.read();
    const changed = Object.keys(current).filter((k) => JSON.stringify(current[k]) !== JSON.stringify(this.saved[k]));
    this.state.textContent = changed.length ? `${changed.length} alteração(ões) não salvas` : "Sem alterações";
    this.state.classList.toggle("is-dirty", changed.length > 0);
  }

  async save(e) {
    e.preventDefault();
    if (!this.form.reportValidity()) return;

    const body = this.read();
    if (body.enabled && !body.dry_run && !(this.saved?.enabled && !this.saved?.dry_run)) {
      if (!confirm("Ligar os agentes ao vivo no agendamento? Eles vão construir, recrutar, coletar e saquear sozinhos.")) return;
    }

    const button = this.form.querySelector("button[type=submit]");
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    try {
      this.saved = await this.api.send("/agents/settings", "PATCH", body);
      this.fill(this.saved);
      this.markDirty();
      this.toast.show("Configurações salvas — valem a partir do próximo minuto");
    } catch (err) {
      this.toast.show(err.message, true);
    } finally {
      button.disabled = false;
      button.removeAttribute("aria-busy");
    }
  }

  async loadSystem() {
    let info;
    try {
      info = await this.api.get("/system/info");
    } catch {
      return;
    }

    const ai = info.ai;
    const status = ai.active ? Html.badge(`${Html.icon("check")}ativa`, "success") : Html.badge(Format.esc(ai.error || "desligada"), ai.provider === "none" ? "neutral" : "danger");
    document.getElementById("ai-card").innerHTML = [
      ["Status", status],
      ["Provedor", Format.esc(ai.provider)],
      ["Modelo", Format.esc(ai.model || "—")],
      ["Endereço", Format.esc(ai.base_url || "padrão do SDK")],
      ["Chave", ai.key_configured ? Html.badge("configurada", "success") : Html.badge("ausente", "warning")],
    ].map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("");

    document.getElementById("system-info").innerHTML = [
      ["Mundo", `${Format.esc(info.server)} · ${Format.esc(info.world_url)}`],
      ["Sincronização da conta", `a cada ${info.sync_interval_seconds} s`],
      ["Dados do mundo", `a cada ${info.world_sync_interval_minutes} min`],
      ["Horário de silêncio", Format.esc(info.quiet_hours || "nenhum")],
      ["Navegador", info.headless ? "oculto (headless)" : "visível"],
      ["Banco de dados", Format.esc(info.database)],
      ["Retenção", `rodadas ${info.trace_retention_days} dias · logs ${info.log_retention_days} dias`],
      ["Versão", `v${Format.esc(info.version)}`],
    ].map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("");
  }
}

new SettingsPage().start();
