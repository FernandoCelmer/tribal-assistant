import { Busy, Format, Html, Page, VillagePicker } from "/static/js/core.js";

class SurroundingsPage extends Page {
  constructor() {
    super({ every: 60000 });
    this.picker = new VillagePicker(document.getElementById("village-select"));
    this.kind = document.getElementById("nearby-kind");
    this.radius = document.getElementById("nearby-radius");
    this.body = document.getElementById("nearby");

    for (const el of [this.kind, this.radius]) el.addEventListener("change", () => this.loadNearby());
    this.picker.onChange(() => this.loadNearby());

    this.body.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-farm]");
      if (!btn) return;
      Busy.run(btn, async () => {
        await this.api.send("/farm/targets", "POST", { coords: btn.dataset.farm, template: "A", wall_level: 0 });
        this.toast.show(`${btn.dataset.farm} adicionada ao farm`);
      }, () => this.loadNearby());
    });
  }

  async refresh() {
    try {
      const overview = await this.api.get("/game/overview");
      this.picker.update(overview.villages);
    } catch {}
    await this.loadNearby();
  }

  async loadNearby() {
    const v = this.picker.current();
    if (!v) {
      this.body.innerHTML = Html.empty(8, "Sincronize uma aldeia primeiro.");
      return;
    }

    try {
      const status = await this.api.get("/world/status");
      document.getElementById("world-meta").textContent = status.fetched_at
        ? `${Format.number.format(status.villages)} aldeias no mundo · velocidade ${status.speed}x · dados de ${Format.when(status.fetched_at)}`
        : "baixando dados do mundo…";

      const rows = await this.api.get(`/world/nearby?village_id=${v.id}&kind=${this.kind.value}&radius=${this.radius.value}&limit=60`);
      this.body.innerHTML = rows.length ? rows.map((n) => `<tr>
        <td>${Format.esc(n.name)}</td><td>${Format.esc(n.coords)}</td><td class="num">${Format.number.format(n.points)}</td>
        <td class="num">${n.distance.toFixed(1)}</td>
        <td>${n.is_barbarian ? `<span class="muted">bárbara</span>` : `${Format.esc(n.player_name || "?")}${n.ally_tag ? ` <span class="muted">[${Format.esc(n.ally_tag)}]</span>` : ""}`}</td>
        <td class="num">${n.travel_minutes.spear != null ? Format.duration(n.travel_minutes.spear * 60) : "—"}</td>
        <td class="num">${n.travel_minutes.light != null ? Format.duration(n.travel_minutes.light * 60) : "—"}</td>
        <td><div class="row-actions">${n.is_barbarian ? (n.is_farm_target ? Html.badge("no farm", "success") : `<button class="btn btn--sm" type="button" data-farm="${Format.esc(n.coords)}" aria-label="Adicionar ${Format.esc(n.coords)} ao farm">${Html.icon("plus")}farm</button>`) : ""}</div></td></tr>`).join("")
        : Html.empty(8, "Nada neste raio.");
    } catch (e) {
      this.body.innerHTML = Html.empty(8, Format.esc(e.message));
    }
  }
}

new SurroundingsPage().start();
