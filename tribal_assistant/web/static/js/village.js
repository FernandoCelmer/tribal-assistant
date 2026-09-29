import { Countdown, Format, Html, Page, UNIT_LABELS, VillagePicker } from "/static/js/core.js";

class VillagePage extends Page {
  constructor() {
    super({ every: 15000 });
    this.picker = new VillagePicker(document.getElementById("village-select"));
    this.picker.onChange(() => this.render());
    Countdown.start();
  }

  async refresh() {
    try {
      const overview = await this.api.get("/game/overview");
      this.picker.update(overview.villages);
    } catch {
      return;
    }
    this.render();
  }

  render() {
    const v = this.picker.current();
    document.getElementById("village-empty").hidden = !!v;
    document.getElementById("army").hidden = !v;
    if (!v) return;

    document.getElementById("v-meta").textContent = `${v.name} · ${v.coords} · sync ${Format.when(v.synced_at)}`;
    const num = (n) => (n == null ? "—" : Format.number.format(n));

    document.getElementById("units").innerHTML = v.units.length ? v.units.map((u) => `
      <tr class="${u.total || u.available ? "" : "is-dim"}">
        <td>${Format.esc(UNIT_LABELS[u.name] || u.name)}</td><td class="num"><b>${Format.number.format(u.home)}</b></td>
        <td class="num">${Format.number.format(u.away)}</td><td class="num">${Format.number.format(u.total)}</td>
        <td class="num">${u.available ? Format.number.format(u.max_recruit) : "—"}</td>
        <td class="num res--wood">${num(u.cost_wood)}</td><td class="num res--clay">${num(u.cost_clay)}</td>
        <td class="num res--iron">${num(u.cost_iron)}</td><td class="num">${num(u.cost_pop)}</td>
        <td class="num">${u.build_time == null ? "—" : Format.duration(u.build_time)}</td>
        <td>${u.available ? Html.badge("recrutável", "success") : Html.badge(Format.esc(u.blocker || "indisponível"))}</td></tr>`).join("")
      : Html.empty(11, "Sem dados de tropas.");

    document.getElementById("recruit-queue").innerHTML = v.recruit_orders.length
      ? "Recrutando: " + v.recruit_orders.map((r) => `${r.count} ${Format.esc(UNIT_LABELS[r.unit] || r.unit)} <span data-until="${Format.esc(r.finishes_at || "")}"></span>`).join(" · ")
      : "Nenhum recrutamento em andamento.";

    document.getElementById("buildings").innerHTML = v.buildings.map((b) => {
      const queued = b.queued_level ? `→ ${b.queued_level} <span class="muted" data-until="${Format.esc(b.queued_until || "")}"></span>` : "";
      const status = b.can_build ? Html.badge("pode", "success") : b.blocker ? Html.badge(Format.esc(b.blocker)) : Html.badge("sem recursos", "warning");
      return `<tr class="${b.level === 0 && !b.can_build ? "is-dim" : ""}">
        <td>${Format.esc(b.label)}</td><td class="num">${b.level}${b.max_level ? `<span class="muted">/${b.max_level}</span>` : ""}</td>
        <td>${queued}</td>
        <td class="num res--wood">${num(b.next_wood)}</td><td class="num res--clay">${num(b.next_clay)}</td>
        <td class="num res--iron">${num(b.next_iron)}</td><td class="num">${num(b.next_pop)}</td>
        <td class="num">${b.build_time == null ? "—" : Format.duration(b.build_time)}</td><td>${status}</td></tr>`;
    }).join("");

    Countdown.tick();
  }
}

new VillagePage().start();
