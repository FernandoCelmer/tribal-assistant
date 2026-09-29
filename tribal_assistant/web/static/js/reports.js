import { Format, Html, Page } from "/static/js/core.js";

const RESULTS = { green: "vitória sem perdas", yellow: "vitória com perdas", red: "derrota", blue: "espionagem" };

class ReportsPage extends Page {
  constructor() {
    super({ every: 30000 });
  }

  async refresh() {
    let overview;
    try {
      overview = await this.api.get("/game/overview");
    } catch {
      return;
    }

    const list = overview.reports || [];
    document.getElementById("r-count").textContent = `(${list.length})`;
    document.getElementById("reports").innerHTML = list.length ? list.map((r) => {
      const loot = r.loot_wood + r.loot_clay + r.loot_iron;
      const label = RESULTS[r.result] || "sem resultado";
      return `<tr>
        <td><span class="dot ${RESULTS[r.result] ? `dot--${r.result}` : ""}" title="${label}" aria-hidden="true"></span><span class="sr-only">${label}</span></td>
        <td>${r.is_new ? "<b>" : ""}${Format.esc(r.title)}${r.is_new ? "</b>" : ""}</td>
        <td>${Format.esc(r.target_coords || "")}</td>
        <td class="muted">${Format.when(r.received_at)}</td>
        <td class="num res--wood">${r.loot_wood ? Format.number.format(r.loot_wood) : "—"}</td>
        <td class="num res--clay">${r.loot_clay ? Format.number.format(r.loot_clay) : "—"}</td>
        <td class="num res--iron">${r.loot_iron ? Format.number.format(r.loot_iron) : "—"}</td>
        <td class="num">${loot ? `${Format.number.format(loot)}${r.haul_total ? `/${Format.number.format(r.haul_total)}` : ""}` : "—"}</td></tr>`;
    }).join("") : Html.empty(8, "Nenhum relatório.");
  }
}

new ReportsPage().start();
