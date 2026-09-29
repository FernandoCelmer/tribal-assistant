import { Busy, Format, Html, Page } from "/static/js/core.js";

class FarmPage extends Page {
  constructor() {
    super({ every: 20000 });
    this.bind();
  }

  async refresh() {
    const rows = await this.api.get("/farm/targets").catch(() => []);
    document.getElementById("t-count").textContent = `(${rows.length})`;
    document.getElementById("targets").innerHTML = rows.length ? rows.map((t) => `<tr>
        <td>${Format.esc(t.coords)}</td><td>${Format.esc(t.template)}</td>
        <td class="num">${t.wall_level}</td>
        <td>${Html.pill(t.enabled, "sim", "não")}</td>
        <td class="muted">${Format.when(t.last_attack_at)}</td>
        <td class="num">${Format.number.format(t.last_loot)}</td></tr>`).join("")
      : Html.empty(6, "Nenhum alvo. Adicione acima ou pela página Arredores.");
  }

  bind() {
    document.getElementById("btn-tick").addEventListener("click", (e) => Busy.run(e.currentTarget, async () => {
      const r = await this.api.send("/farm/tick");
      this.toast.show(`Enviados: ${r.dispatched} · pulados: ${r.skipped}${r.errors.length ? ` · erros: ${r.errors.join("; ")}` : ""}`, r.errors.length > 0);
    }, () => this.tick()));

    document.getElementById("target-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const form = e.target;
      const f = new FormData(form);
      Busy.run(form.querySelector("button"), async () => {
        await this.api.send("/farm/targets", "POST", { coords: f.get("coords"), template: f.get("template"), wall_level: Number(f.get("wall_level")) });
        form.reset();
        this.toast.show("Alvo adicionado");
      }, () => this.tick());
    });
  }
}

new FarmPage().start();
