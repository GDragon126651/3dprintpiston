const $ = (id) => document.getElementById(id);

let payload;

function terms(values) {
  const out = [1, ...values];
  values.forEach((v) => out.push(v * v));
  for (let i = 0; i < values.length; i += 1) {
    for (let j = i + 1; j < values.length; j += 1) out.push(values[i] * values[j]);
  }
  return out;
}

function predict(target, rawFeatures) {
  const distances = payload.rows
    .map((row) => {
      const d = Math.sqrt(
        payload.features.reduce((sum, feature, i) => {
          const z = (rawFeatures[i] - row[feature]) / payload.knn.feature_std[i];
          return sum + z * z;
        }, 0),
      );
      return [d, row[target]];
    })
    .sort((a, b) => a[0] - b[0])
    .slice(0, payload.knn.k);
  if (distances[0][0] < 1e-12) return distances[0][1];
  const weights = distances.map(([d]) => 1 / (Math.pow(d, payload.knn.distance_power) + 1e-9));
  const totalWeight = weights.reduce((a, b) => a + b, 0);
  return distances.reduce((sum, item, i) => sum + item[1] * weights[i], 0) / totalWeight;
}

function featureVector(power, speed, hatch) {
  const layer = 0.06;
  return [
    power,
    speed,
    hatch,
    power / speed,
    power / (speed * hatch * layer),
    power / Math.sqrt(speed),
    (power * speed) / 1000,
  ];
}

function costIndex(power, speed, hatch) {
  const layer = 0.06;
  const depositionRate = Math.max(speed * hatch * layer, 0.001);
  const normalizedMachineTime = 1 / depositionRate;
  const energyFactor = power / 260;
  const powderRisk = 1 + 0.18 * Math.max(0, hatch - 0.12) / 0.03;
  return normalizedMachineTime * energyFactor * powderRisk;
}

function candidateEstimate(power, speed, hatch) {
  const x = featureVector(power, speed, hatch);
  const p = {};
  payload.targets.forEach((target) => {
    p[target] = predict(target, x);
  });
  p.xct_porosity_pct = Math.max(0, p.xct_porosity_pct);
  const density = 2.67 * (1 - Math.min(p.xct_porosity_pct, 20) / 100);
  const strengthToWeight = p.uts_mpa / density;
  p.cost_index = costIndex(power, speed, hatch);
  p.predicted_mass_saving_pct = Math.max(0, Math.min(18, 4 + 0.03 * (p.yield_mpa - 180) + 0.2 * p.elongation_pct));
  p.thermal_relief_score = Math.max(0, Math.min(100, 100 - 10 * p.roughness_avg_um - 16 * p.xct_porosity_pct));
  p.performance_index =
    0.33 * strengthToWeight +
    2.1 * p.elongation_pct +
    1.4 * p.predicted_mass_saving_pct +
    0.22 * p.thermal_relief_score -
    4.5 * p.xct_porosity_pct;
  p.value_score = p.performance_index / (1 + 0.012 * p.cost_index);
  return p;
}

function fmt(value, digits = 1) {
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function renderMetrics() {
  const labels = {
    uts_mpa: "UTS",
    yield_mpa: "Yield",
    elongation_pct: "Elongation",
    xct_porosity_pct: "Porosity",
    roughness_avg_um: "Roughness",
    hardness_hv: "Hardness",
  };
  $("metrics").innerHTML = payload.targets
    .map((target) => {
      const metric = payload.metrics[target];
      return `<div class="metric"><span>${labels[target]} model</span><strong>R2 ${fmt(metric.r2, 2)}</strong><small>MAE ${fmt(metric.mae, 2)} / RMSE ${fmt(metric.rmse, 2)}</small></div>`;
    })
    .join("");
}

function renderCandidates() {
  $("candidateRows").innerHTML = payload.top_candidates
    .slice(0, 18)
    .map(
      (c, i) => `<tr>
        <td>${i + 1}</td>
        <td>${fmt(c.power_w, 0)}</td>
        <td>${fmt(c.scan_speed_mm_s, 0)}</td>
        <td>${fmt(c.hatch_spacing_mm, 3)}</td>
        <td>${fmt(c.uts_mpa)}</td>
        <td>${fmt(c.yield_mpa)}</td>
        <td>${fmt(c.xct_porosity_pct, 2)}%</td>
        <td>${fmt(c.cost_index, 2)}</td>
        <td>${fmt(c.value_score, 1)}</td>
      </tr>`,
    )
    .join("");
}

function drawMap(selected) {
  const canvas = $("map");
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  const margin = { left: 68, right: 28, top: 28, bottom: 54 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  let min = Infinity;
  let max = -Infinity;
  const cells = [];
  for (let p = 120; p <= 420; p += 10) {
    for (let s = 300; s <= 1600; s += 25) {
      const c = candidateEstimate(p, s, selected.hatch);
      min = Math.min(min, c.value_score);
      max = Math.max(max, c.value_score);
      cells.push({ p, s, v: c.value_score });
    }
  }
  cells.forEach(({ p, s, v }) => {
    const x = margin.left + ((s - 300) / 1300) * plotW;
    const y = margin.top + plotH - ((p - 120) / 300) * plotH;
    const t = (v - min) / (max - min || 1);
    ctx.fillStyle = `rgb(${35 + 220 * t}, ${58 + 95 * t}, ${84 - 42 * t})`;
    ctx.fillRect(x, y, Math.ceil(plotW / 53) + 1, Math.ceil(plotH / 31) + 1);
  });
  ctx.strokeStyle = "#f1f5f9";
  ctx.lineWidth = 2;
  const sx = margin.left + ((selected.speed - 300) / 1300) * plotW;
  const sy = margin.top + plotH - ((selected.power - 120) / 300) * plotH;
  ctx.beginPath();
  ctx.arc(sx, sy, 8, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fillStyle = "#f1f5f9";
  ctx.font = "15px system-ui";
  ctx.fillText("Scan speed mm/s", margin.left + plotW / 2 - 58, height - 15);
  ctx.save();
  ctx.translate(18, margin.top + plotH / 2 + 50);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Laser power W", 0, 0);
  ctx.restore();
}

function drawCorrelations() {
  const canvas = $("corr");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const target = "uts_mpa";
  const rows = Object.entries(payload.correlations[target]).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const left = 170;
  const mid = 385;
  ctx.font = "14px system-ui";
  rows.forEach(([name, value], i) => {
    const y = 36 + i * 42;
    ctx.fillStyle = "#9da8b7";
    ctx.textAlign = "right";
    ctx.fillText(name, left - 14, y + 5);
    ctx.fillStyle = value >= 0 ? "#42d4c8" : "#f05a28";
    const w = value * 180;
    ctx.fillRect(mid, y - 11, w, 22);
    ctx.fillStyle = "#f1f5f9";
    ctx.textAlign = value >= 0 ? "left" : "right";
    ctx.fillText(fmt(value, 2), mid + w + (value >= 0 ? 8 : -8), y + 5);
  });
  ctx.strokeStyle = "#303946";
  ctx.beginPath();
  ctx.moveTo(mid, 16);
  ctx.lineTo(mid, canvas.height - 20);
  ctx.stroke();
}

function updatePrediction() {
  const power = Number($("power").value);
  const speed = Number($("speed").value);
  const hatch = Number($("hatch").value);
  $("powerOut").textContent = `${power} W`;
  $("speedOut").textContent = `${speed} mm/s`;
  $("hatchOut").textContent = `${fmt(hatch, 3)} mm`;
  const p = candidateEstimate(power, speed, hatch);
  $("prediction").innerHTML = [
    ["UTS", `${fmt(p.uts_mpa)} MPa`],
    ["Yield", `${fmt(p.yield_mpa)} MPa`],
    ["Elongation", `${fmt(p.elongation_pct, 2)}%`],
    ["Porosity", `${fmt(p.xct_porosity_pct, 2)}%`],
    ["Mass saving", `${fmt(p.predicted_mass_saving_pct, 1)}%`],
    ["Cost index", fmt(p.cost_index, 2)],
    ["Value score", fmt(p.value_score, 1)],
  ]
    .map(([k, v]) => `<div><span>${k}</span><strong>${v}</strong></div>`)
    .join("");
  drawMap({ power, speed, hatch });
}

function renderSource() {
  const s = payload.source;
  $("source").innerHTML = `Data source: <strong>${s.title}</strong>, ${s.authors}. 
    <a href="${s.zenodo}">Zenodo</a> / <a href="${s.data_article}">Data article</a>.
    License: ${s.license}.`;
}

async function init() {
  const response = await fetch("model_payload.json");
  payload = await response.json();
  const best = payload.top_candidates[0];
  $("bestConcept").textContent = `Value ${fmt(best.value_score, 1)}`;
  $("bestDetail").textContent = `${fmt(best.power_w, 0)} W / ${fmt(best.scan_speed_mm_s, 0)} mm/s / h ${fmt(best.hatch_spacing_mm, 3)} mm`;
  renderMetrics();
  renderCandidates();
  renderSource();
  drawCorrelations();
  ["power", "speed", "hatch"].forEach((id) => $(id).addEventListener("input", updatePrediction));
  updatePrediction();
}

init().catch((error) => {
  document.body.innerHTML = `<pre>${error.stack}</pre>`;
});
