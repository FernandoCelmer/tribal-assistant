import { Format, Html, Page } from "/static/js/core.js";

class AccountsPage extends Page {
  constructor() {
    super({ every: 0 });
    this.body = document.getElementById("accounts-body");
    this.form = document.getElementById("account-form");
    this.form.addEventListener("submit", (e) => this.add(e));
  }

  async refresh() {
    const accounts = await this.api.get("/accounts");
    this.body.innerHTML = accounts.map((a) => `<tr>
      <td><b>${Format.esc(a.name)}</b></td><td>${Format.esc(a.server)}</td><td>${Format.esc(a.username)}</td>
      <td>${a.headless ? "sem janela" : "com janela"}</td>
      <td><label class="check"><input type="checkbox" data-toggle="${a.id}" ${a.enabled ? "checked" : ""}> ${a.enabled ? "jogando" : "pausada"}</label></td>
    </tr>`).join("") || Html.empty(5, "Nenhuma conta cadastrada.");

    for (const box of this.body.querySelectorAll("[data-toggle]")) {
      box.addEventListener("change", () => this.toggle(Number(box.dataset.toggle), box.checked));
    }
  }

  async toggle(id, enabled) {
    try {
      await this.api.send(`/accounts/${id}`, "PATCH", { enabled });
      this.toast.show(enabled ? "Conta voltou a jogar" : "Conta pausada");
      await this.refresh();
    } catch (err) {
      this.toast.show(err.message, true);
    }
  }

  async add(e) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(this.form));
    const body = { world_url: data.world_url, username: data.username, password: data.password, name: data.name || null, headless: !!data.headless };
    try {
      await this.api.send("/accounts", "POST", body);
      this.form.reset();
      this.toast.show("Conta adicionada. Recarregue a página para ela aparecer no seletor.");
      await this.refresh();
    } catch (err) {
      this.toast.show(err.message, true);
    }
  }
}

new AccountsPage().start();
