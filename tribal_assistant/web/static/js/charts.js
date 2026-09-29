const SVG_NS = "http://www.w3.org/2000/svg";

class ChartBase {
  constructor(host, { height = 220, format = (v) => String(v) } = {}) {
    this.host = host;
    this.height = height;
    this.format = format;
    this.margin = { top: 12, right: 12, bottom: 28, left: 44 };
    this.host.classList.add("chart");
    this.host.innerHTML = "";

    this.svg = document.createElementNS(SVG_NS, "svg");
    this.svg.setAttribute("role", "img");
    this.host.appendChild(this.svg);

    this.tooltip = document.createElement("div");
    this.tooltip.className = "chart__tooltip";
    this.tooltip.hidden = true;
    this.host.appendChild(this.tooltip);

    this.host.addEventListener("mouseleave", () => this.hideTip());
  }

  el(name, attrs = {}, parent = this.svg) {
    const node = document.createElementNS(SVG_NS, name);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    parent.appendChild(node);
    return node;
  }

  size() {
    const width = Math.max(260, this.host.clientWidth || 600);
    this.svg.setAttribute("viewBox", `0 0 ${width} ${this.height}`);
    this.svg.setAttribute("width", width);
    this.svg.setAttribute("height", this.height);
    return {
      width,
      innerW: width - this.margin.left - this.margin.right,
      innerH: this.height - this.margin.top - this.margin.bottom,
    };
  }

  niceMax(value) {
    if (value <= 0) return 1;
    const power = 10 ** Math.floor(Math.log10(value));
    const step = [1, 2, 2.5, 5, 10].find((m) => m * power >= value / 4) * power;
    return Math.ceil(value / step) * step;
  }

  yAxis(max, innerW, innerH, ticks = 4) {
    if (max <= 8 && Number.isInteger(max)) ticks = max;
    const g = this.el("g", { class: "chart__axis" });
    for (let i = 0; i <= ticks; i += 1) {
      const value = (max / ticks) * i;
      const y = this.margin.top + innerH - (innerH * i) / ticks;
      this.el("line", { x1: this.margin.left, x2: this.margin.left + innerW, y1: y, y2: y, class: i === 0 ? "chart__baseline" : "chart__grid" }, g);
      const label = this.el("text", { x: this.margin.left - 8, y: y + 4, "text-anchor": "end", class: "chart__tick" }, g);
      label.textContent = this.format(Math.round(value));
    }
  }

  showTip(html, x, y) {
    this.tooltip.innerHTML = html;
    this.tooltip.hidden = false;
    const box = this.host.getBoundingClientRect();
    const tip = this.tooltip.getBoundingClientRect();
    let left = x + 14;
    if (left + tip.width > box.width) left = x - tip.width - 14;
    this.tooltip.style.left = `${Math.max(0, left)}px`;
    this.tooltip.style.top = `${Math.max(0, y - tip.height / 2)}px`;
  }

  hideTip() {
    this.tooltip.hidden = true;
  }

  empty(text) {
    this.svg.innerHTML = "";
    const { width } = this.size();
    const t = this.el("text", { x: width / 2, y: this.height / 2, "text-anchor": "middle", class: "chart__empty" });
    t.textContent = text;
  }
}

export class StackedBars extends ChartBase {
  render({ labels, series, tooltipTitle }) {
    this.svg.innerHTML = "";
    const totals = labels.map((_, i) => series.reduce((sum, s) => sum + (s.values[i] || 0), 0));
    const max = this.niceMax(Math.max(0, ...totals));
    if (!totals.some(Boolean)) return this.empty("Sem ações no período");

    const { innerW, innerH } = this.size();
    this.yAxis(max, innerW, innerH);

    const band = innerW / labels.length;
    const barW = Math.max(3, Math.min(28, band * 0.7));
    const scale = (v) => (v / max) * innerH;
    const baseY = this.margin.top + innerH;
    const every = Math.ceil(labels.length / 8);

    labels.forEach((label, i) => {
      const x = this.margin.left + band * i + (band - barW) / 2;
      let y = baseY;
      const segments = series.filter((s) => s.values[i] > 0);

      segments.forEach((s, j) => {
        const h = scale(s.values[i]);
        const gap = j > 0 ? 2 : 0;
        const top = j === segments.length - 1;
        this.el("path", { d: this.barPath(x, y - h + gap, barW, Math.max(0, h - gap), top), fill: s.color, class: "chart__mark" });
        y -= h;
      });

      if (i % every === 0) {
        const t = this.el("text", { x: x + barW / 2, y: baseY + 18, "text-anchor": "middle", class: "chart__tick" });
        t.textContent = label;
      }

      const hit = this.el("rect", { x: this.margin.left + band * i, y: this.margin.top, width: band, height: innerH, class: "chart__hit" });
      hit.addEventListener("mousemove", (e) => {
        const rows = series
          .filter((s) => s.values[i] > 0)
          .map((s) => `<div class="chart__tip-row"><i style="background:${s.color}"></i>${s.name}<b>${this.format(s.values[i])}</b></div>`)
          .join("");
        const box = this.host.getBoundingClientRect();
        this.showTip(`<div class="chart__tip-title">${tooltipTitle(i)}</div>${rows || '<div class="muted">nenhuma ação</div>'}<div class="chart__tip-total">Total <b>${this.format(totals[i])}</b></div>`, e.clientX - box.left, e.clientY - box.top);
      });
    });
  }

  barPath(x, y, w, h, roundTop) {
    if (h <= 0) return "";
    const r = roundTop ? Math.min(4, w / 2, h) : 0;
    return `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h} Z`;
  }
}

export class HorizontalBars extends ChartBase {
  render({ rows, color }) {
    this.svg.innerHTML = "";
    if (!rows.length) {
      this.height = 120;
      return this.empty("Nenhuma recusa no período");
    }

    this.height = rows.length * 34 + 16;
    const { width } = this.size();
    const max = Math.max(...rows.map((r) => r.count));
    const labelW = Math.min(width * 0.55, 320);
    const barMax = width - labelW - 56;

    rows.forEach((row, i) => {
      const y = 8 + i * 34;
      const label = this.el("text", { x: 0, y: y + 16, class: "chart__label" });
      label.textContent = row.label.length > 52 ? `${row.label.slice(0, 51)}…` : row.label;
      const w = Math.max(3, (row.count / max) * barMax);
      this.el("path", { d: `M${labelW},${y + 4} H${labelW + w - 4} Q${labelW + w},${y + 4} ${labelW + w},${y + 8} V${y + 16} Q${labelW + w},${y + 20} ${labelW + w - 4},${y + 20} H${labelW} Z`, fill: color, class: "chart__mark" });
      const value = this.el("text", { x: labelW + w + 8, y: y + 16, class: "chart__value" });
      value.textContent = this.format(row.count);
    });
  }
}

export class Lines extends ChartBase {
  render({ times, series }) {
    this.svg.innerHTML = "";
    if (times.length < 2) return this.empty("Poucos dados ainda — cada sincronização adiciona um ponto");

    const all = series.flatMap((s) => s.values).filter((v) => v != null);
    const max = this.niceMax(Math.max(...all));
    const { innerW, innerH } = this.size();
    this.yAxis(max, innerW, innerH);

    const t0 = times[0].getTime();
    const span = Math.max(1, times[times.length - 1].getTime() - t0);
    const x = (t) => this.margin.left + ((t.getTime() - t0) / span) * innerW;
    const y = (v) => this.margin.top + innerH - (v / max) * innerH;
    const baseY = this.margin.top + innerH;

    const tickCount = Math.min(6, times.length);
    for (let i = 0; i < tickCount; i += 1) {
      const t = times[Math.round((i * (times.length - 1)) / Math.max(1, tickCount - 1))];
      const label = this.el("text", { x: x(t), y: baseY + 18, "text-anchor": "middle", class: "chart__tick" });
      label.textContent = t.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
    }

    const lastIndex = times.length - 1;
    const labels = [];

    for (const s of series) {
      const d = s.values.map((v, i) => (v == null ? null : `${x(times[i])},${y(v)}`)).filter(Boolean);
      this.el("polyline", { points: d.join(" "), fill: "none", stroke: s.color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round", class: "chart__line" });
      if (series.length > 1 && s.values[lastIndex] != null) labels.push({ name: s.name, y: y(s.values[lastIndex]) - 8 });
    }

    labels.sort((a, b) => a.y - b.y);
    for (let i = 1; i < labels.length; i += 1) {
      labels[i].y = Math.max(labels[i].y, labels[i - 1].y + 14);
    }
    for (const item of labels) {
      const label = this.el("text", { x: this.margin.left + innerW - 4, y: Math.min(item.y, baseY - 4), "text-anchor": "end", class: "chart__label chart__label--halo" });
      label.textContent = item.name;
    }

    const cross = this.el("line", { y1: this.margin.top, y2: baseY, class: "chart__crosshair", visibility: "hidden" });
    const dots = series.map((s) => this.el("circle", { r: 4, fill: s.color, class: "chart__dot", visibility: "hidden" }));
    const hit = this.el("rect", { x: this.margin.left, y: this.margin.top, width: innerW, height: innerH, class: "chart__hit" });

    hit.addEventListener("mousemove", (e) => {
      const box = this.host.getBoundingClientRect();
      const svgBox = this.svg.getBoundingClientRect();
      const px = ((e.clientX - svgBox.left) / svgBox.width) * (innerW + this.margin.left + this.margin.right);
      let best = 0;
      times.forEach((t, i) => { if (Math.abs(x(t) - px) < Math.abs(x(times[best]) - px)) best = i; });
      const cx = x(times[best]);
      cross.setAttribute("x1", cx);
      cross.setAttribute("x2", cx);
      cross.setAttribute("visibility", "visible");
      series.forEach((s, j) => {
        const v = s.values[best];
        dots[j].setAttribute("visibility", v == null ? "hidden" : "visible");
        if (v != null) { dots[j].setAttribute("cx", cx); dots[j].setAttribute("cy", y(v)); }
      });
      const rows = series.map((s) => `<div class="chart__tip-row"><i style="background:${s.color}"></i>${s.name}<b>${s.values[best] == null ? "—" : this.format(s.values[best])}</b></div>`).join("");
      this.showTip(`<div class="chart__tip-title">${times[best].toLocaleString("pt-BR")}</div>${rows}`, e.clientX - box.left, e.clientY - box.top);
    });
    hit.addEventListener("mouseleave", () => {
      cross.setAttribute("visibility", "hidden");
      dots.forEach((d) => d.setAttribute("visibility", "hidden"));
    });
  }
}
