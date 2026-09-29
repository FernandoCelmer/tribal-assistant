(() => {
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.querySelector(".sidebar-backdrop");
  const opener = document.querySelector("[data-sidebar-open]");

  const setSidebar = (open) => {
    document.body.classList.toggle("sidebar-open", open);
    if (backdrop) backdrop.hidden = !open;
    opener?.setAttribute("aria-expanded", String(open));
    if (open) sidebar?.querySelector("a, button")?.focus();
  };

  opener?.addEventListener("click", () => setSidebar(true));
  document.querySelectorAll("[data-sidebar-close]").forEach((el) => el.addEventListener("click", () => setSidebar(false)));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && document.body.classList.contains("sidebar-open")) {
      setSidebar(false);
      opener?.focus();
    }
  });

  const root = document.documentElement;
  const themeToggle = document.querySelector("[data-theme-toggle]");
  if (themeToggle) {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const mode = () => root.dataset.theme || (media.matches ? "dark" : "light");
    const paint = () => {
      const m = mode();
      themeToggle.dataset.mode = m;
      themeToggle.setAttribute("aria-pressed", String(m === "dark"));
      themeToggle.querySelector(".theme-toggle__label").textContent = m === "dark" ? "Escuro" : "Claro";
    };
    themeToggle.addEventListener("click", () => {
      const next = mode() === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      try { localStorage.setItem("tw.theme", next); } catch {}
      paint();
    });
    media.addEventListener("change", paint);
    paint();
  }

  const nav = document.querySelector("[data-nav]");

  function closeSubmenus(except) {
    document.querySelectorAll(".nav__menu[open]").forEach((d) => { if (d !== except) d.open = false; });
  }

  if (nav) {
    const toggle = nav.querySelector(".nav__toggle");
    const current = nav.querySelector(".nav__toggle-current");
    const setOpen = (open) => {
      toggle?.setAttribute("aria-expanded", String(open));
      nav.classList.toggle("is-open", open);
    };

    toggle?.addEventListener("click", () => setOpen(toggle.getAttribute("aria-expanded") !== "true"));
    nav.addEventListener("click", (e) => {
      if (e.target.closest("a")) { setOpen(false); closeSubmenus(); }
    });
    nav.querySelectorAll(".nav__menu").forEach((d) => d.addEventListener("toggle", () => d.open && closeSubmenus(d)));
    document.addEventListener("click", (e) => { if (!e.target.closest(".nav__menu")) closeSubmenus(); });
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      const open = nav.querySelector(".nav__menu[open]");
      if (open) { open.open = false; open.querySelector("summary").focus(); return; }
      if (nav.classList.contains("is-open")) { setOpen(false); toggle.focus(); }
    });

    const links = [...nav.querySelectorAll('a.nav__link[href^="#"]')];
    const sections = links.map((a) => [a, document.getElementById(a.hash.slice(1))]).filter(([, el]) => el);
    let frame = 0;
    const update = () => {
      frame = 0;
      const visible = sections.filter(([, el]) => el.offsetParent !== null);
      if (!visible.length) return;
      const line = nav.getBoundingClientRect().bottom + 24;
      let active = visible[0][0];
      for (const [a, el] of visible) if (el.getBoundingClientRect().top <= line) active = a;
      const atBottom = innerHeight + scrollY >= document.documentElement.scrollHeight - 2;
      if (atBottom) active = visible[visible.length - 1][0];
      for (const [a] of sections) {
        if (a === active) a.setAttribute("aria-current", "location");
        else a.removeAttribute("aria-current");
      }
      if (current) current.textContent = active.textContent.trim();
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
    if (sections.length) {
      addEventListener("scroll", schedule, { passive: true });
      addEventListener("resize", schedule);
      new MutationObserver(schedule).observe(document.body, { attributes: true, attributeFilter: ["hidden"], subtree: true });
      update();
    }
  }

  for (const list of document.querySelectorAll('[role="tablist"]')) {
    const tabs = [...list.querySelectorAll('[role="tab"]')];
    const select = (tab, focus) => {
      for (const t of tabs) {
        const on = t === tab;
        t.setAttribute("aria-selected", String(on));
        t.tabIndex = on ? 0 : -1;
        const panel = document.getElementById(t.getAttribute("aria-controls"));
        if (panel) panel.hidden = !on;
      }
      if (focus) tab.focus();
    };
    list.addEventListener("click", (e) => { const t = e.target.closest('[role="tab"]'); if (t) select(t); });
    list.addEventListener("keydown", (e) => {
      const i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      const next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
      if (next === undefined) return;
      e.preventDefault();
      select(tabs[(next + tabs.length) % tabs.length], true);
    });
  }

  document.addEventListener("click", (e) => {
    const opener = e.target.closest("[data-dialog-open]");
    if (opener) { document.getElementById(opener.dataset.dialogOpen)?.showModal(); return; }
    const closer = e.target.closest("[data-dialog-close]");
    if (closer) { closer.closest("dialog")?.close(closer.value || ""); return; }
    if (e.target instanceof HTMLDialogElement && e.target.open) e.target.close();
  });

  const wraps = document.querySelectorAll(".table-scroll");
  const hints = new Map();
  for (const wrap of wraps) {
    wrap.tabIndex = 0;
    if (!wrap.hasAttribute("role")) wrap.setAttribute("role", "region");
    const hint = document.createElement("p");
    hint.className = "scroll-hint";
    hint.hidden = true;
    hint.setAttribute("aria-hidden", "true");
    hint.innerHTML = 'Deslize a tabela para ver mais colunas <svg class="icon" aria-hidden="true"><use href="/static/icons.svg#i-arrow-right"/></svg>';
    wrap.before(hint);
    hints.set(wrap, hint);
  }
  const check = (wrap) => { const h = hints.get(wrap); if (h) h.hidden = wrap.scrollWidth <= wrap.clientWidth + 1; };
  if ("ResizeObserver" in window) {
    const ro = new ResizeObserver((entries) => entries.forEach((e) => check(e.target.closest(".table-scroll"))));
    wraps.forEach((w) => { ro.observe(w); if (w.firstElementChild) ro.observe(w.firstElementChild); });
  }
})();
