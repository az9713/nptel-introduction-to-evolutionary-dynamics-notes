"use strict";
(() => {
  const byId = id => document.getElementById(id);
  if (!byId("moran-n")) return;
  const svgNS = "http://www.w3.org/2000/svg";
  const colors = ["#2dd4bf", "#fb923c"];
  const fmt = (x, digits = 5) => Number(x).toLocaleString("en-US", {
    maximumFractionDigits: digits, minimumFractionDigits: 0
  });
  function transition(n, i, r) {
    if (i === 0 || i === n) return [0, 0, 1];
    const denominator = r * i + n - i;
    const up = (r * i / denominator) * ((n - i) / n);
    const down = ((n - i) / denominator) * (i / n);
    return [up, down, 1 - up - down];
  }
  function fixation(n, i, r) {
    if (i === 0) return 0;
    if (i === n) return 1;
    if (r === 1) return i / n;
    const l = Math.log(r);
    if (l > 0) return Math.expm1(-i * l) / Math.expm1(-n * l);
    return Math.exp((n - i) * l) * Math.expm1(i * l)
      / Math.expm1(n * l);
  }
  function times(n, r) {
    const c = [], d = [], result = Array(n + 1).fill(0);
    for (let i = 1; i < n; ++i) {
      const [up, down] = transition(n, i, r);
      const pivot = up + down + (i > 1 ? down * c[i - 2] : 0);
      c.push(i < n - 1 ? -up / pivot : 0);
      d.push((1 + (i > 1 ? down * d[i - 2] : 0)) / pivot);
    }
    for (let i = n - 1; i > 0; --i) {
      result[i] = d[i - 1] - c[i - 1] * result[i + 1];
    }
    return result;
  }
  function node(tag, attributes, text) {
    const item = document.createElementNS(svgNS, tag);
    Object.entries(attributes).forEach(([key, value]) => item.setAttribute(key, value));
    if (text !== undefined) item.textContent = text;
    return item;
  }
  function chart(id, series, xMax, yMax, xLabel, yLabel, point) {
    const svg = byId(id);
    svg.replaceChildren();
    const left = 75, right = 670, top = 48, bottom = 260;
    const px = x => left + x / xMax * (right - left);
    const py = y => bottom - y / yMax * (bottom - top);
    for (let j = 0; j <= 4; ++j) {
      const x = j * xMax / 4, y = j * yMax / 4;
      svg.append(node("line", {x1: left, y1: py(y), x2: right, y2: py(y), class: "lab-grid"}));
      const yTick = yMax >= 100000 && y > 0 ? y.toExponential(1) : fmt(y, 2);
      svg.append(node("text", {x: left - 10, y: py(y) + 4, "text-anchor": "end"}, yTick));
      svg.append(node("text", {x: px(x), y: bottom + 23, "text-anchor": "middle"}, fmt(x, 2)));
    }
    svg.append(node("line", {x1: left, y1: top, x2: left, y2: bottom, class: "lab-axis"}));
    svg.append(node("line", {x1: left, y1: bottom, x2: right, y2: bottom, class: "lab-axis"}));
    svg.append(node("text", {x: left, y: 18}, yLabel));
    svg.append(node("text", {x: (left + right) / 2, y: 307, "text-anchor": "middle"}, xLabel));
    series.forEach((s, j) => {
      svg.append(node("polyline", {points: s.data.map(([x, y]) => `${px(x)},${py(y)}`).join(" "),
        class: "lab-series", stroke: colors[j], "data-series": s.name}));
      const lx = left + j * 260;
      svg.append(node("line", {x1: lx, y1: 35, x2: lx + 25, y2: 35, stroke: colors[j], "stroke-width": 3}));
      svg.append(node("text", {x: lx + 33, y: 39}, s.name));
    });
    if (point) svg.append(node("circle", {cx: px(point[0]), cy: py(point[1]), r: 5,
      fill: colors[0], class: "lab-point"}));
  }
  function results(id, entries) {
    const panel = byId(id);
    panel.replaceChildren();
    for (const [value, label] of entries) {
      const box = document.createElement("div");
      box.className = "lab-result";
      const strong = document.createElement("strong"), span = document.createElement("span");
      strong.textContent = value;
      span.textContent = label;
      box.append(strong, span);
      panel.append(box);
    }
  }
  function updateMoran() {
    const n = Number(byId("moran-n").value);
    byId("moran-i").max = n;
    if (Number(byId("moran-i").value) > n) byId("moran-i").value = n;
    const i = Number(byId("moran-i").value), r = 10 ** Number(byId("moran-r").value);
    byId("moran-n-value").textContent = n;
    byId("moran-i-value").textContent = i;
    byId("moran-r-value").textContent = r.toFixed(4);
    const u = fixation(n, i, r), [up, down, stay] = transition(n, i, r);
    results("fixation-results", [[fmt(u, 8), "Selected fixation probability"],
      [fmt(i / n, 8), "Neutral fixation probability"], [fmt(1 - u, 8), "Selected extinction probability"],
      [fmt(up, 8), "One-event count increase"], [fmt(down, 8), "One-event count decrease"],
      [fmt(stay, 8), "One-event unchanged count"]]);
    const selected = Array.from({length: n + 1}, (_, j) => [j / n, fixation(n, j, r)]);
    chart("fixation-plot", [{name: "Selected", data: selected},
      {name: "Neutral", data: [[0, 0], [1, 1]]}], 1, 1, "Initial mutant fraction i/N",
      "Fixation probability", [i / n, u]);
    const t = times(n, r), neutral = times(n, 1);
    results("time-results", [[fmt(t[i], 6), "Selected mean absorption events"],
      [fmt(neutral[i], 6), "Neutral mean absorption events"],
      [fmt(t[i] / n, 6), "Selected nominal generations"],
      [up + down > 0 ? fmt(1 / (up + down), 6) : "Already absorbed",
        "Mean events to next count change"]]);
    chart("time-plot", [{name: "Selected", data: t.map((v, j) => [j / n, v])},
      {name: "Neutral", data: neutral.map((v, j) => [j / n, v])}], 1,
      Math.max(...t, ...neutral) * 1.08, "Initial mutant fraction i/N",
      "Mean absorption time (attempted events)", [i / n, t[i]]);
  }
  function updateGrowth() {
    const g = Number(byId("growth-rate").value), delta = Number(byId("selection-rate").value);
    const end = Number(byId("growth-time").value), initial = 100, capacity = 10000, x0 = 0.02;
    byId("growth-rate-value").textContent = g.toFixed(2);
    byId("selection-rate-value").textContent = delta.toFixed(2);
    byId("growth-time-value").textContent = end.toFixed(1);
    const exponential = t => initial * Math.exp(g * t);
    const logistic = t => capacity / (1 + ((capacity - initial) / initial) * Math.exp(-g * t));
    const frequency = t => 1 / (1 + ((1 - x0) / x0) * Math.exp(-delta * t));
    results("growth-results", [[fmt(exponential(end), 3), "Exponential cells at final time"],
      [fmt(logistic(end), 3), "Logistic cells at final time"],
      [fmt(frequency(end), 8), "Mutant type B frequency at final time"]]);
    const sample = fn => Array.from({length: 121}, (_, j) => [end * j / 120, fn(end * j / 120)]);
    chart("growth-plot", [{name: "Exponential", data: sample(exponential)},
      {name: "Logistic", data: sample(logistic)}], end,
      exponential(end) * 1.08, "Time (hours)", "Deterministic abundance (cells)");
    chart("selection-plot", [{name: "Mutant type B frequency", data: sample(frequency)}], end,
      Math.max(x0, frequency(end)) * 1.15, "Time (hours)", "Mutant frequency (dimensionless)");
  }
  ["moran-n", "moran-i", "moran-r"].forEach(id => byId(id).addEventListener("input", updateMoran));
  ["growth-rate", "selection-rate", "growth-time"].forEach(id => byId(id).addEventListener("input", updateGrowth));
  updateMoran();
  updateGrowth();
  document.querySelectorAll(".codewrap").forEach(wrap => {
    const readerButton = wrap.querySelector("pre .copy-code");
    if (!readerButton) return;
    wrap.querySelector(":scope > .copybtn")?.remove();
    readerButton.classList.add("copybtn");
  });
  window.EvolutionLab = Object.freeze({transition, fixation, times});
})();
