const fmt = (value, digits = 2) =>
  Number(value).toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });

const metricLabel = {
  ultimate_tensile_strength_mpa: "Ultimate tensile strength",
  yield_strength_mpa: "Yield strength",
  elongation_to_fracture_pct: "Elongation to fracture",
  xct_porosity_pct: "XCT porosity",
  vickers_hardness_hv: "Vickers hardness",
  youngs_modulus_gpa: "Young's modulus",
};

function drawMetricChart(metrics) {
  const canvas = document.getElementById("metricsChart");
  const ctx = canvas.getContext("2d");
  const rows = Object.entries(metrics);
  const margin = { left: 210, top: 26, right: 34, bottom: 24 };
  const chartWidth = canvas.width - margin.left - margin.right;
  const rowHeight = 52;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = "14px system-ui";
  ctx.strokeStyle = "#303946";
  ctx.beginPath();
  ctx.moveTo(margin.left, 10);
  ctx.lineTo(margin.left, canvas.height - 16);
  ctx.stroke();

  rows.forEach(([target, metric], index) => {
    const y = margin.top + index * rowHeight;
    const r2 = Math.max(-0.2, Math.min(1, metric.r2));
    const barWidth = ((r2 + 0.2) / 1.2) * chartWidth;

    ctx.fillStyle = "#9ca8b8";
    ctx.textAlign = "right";
    ctx.fillText(metricLabel[target] || target, margin.left - 16, y + 18);

    ctx.fillStyle = r2 >= 0.55 ? "#53d769" : r2 >= 0.25 ? "#f0b428" : "#f05a28";
    ctx.fillRect(margin.left, y, barWidth, 26);

    ctx.fillStyle = "#f3f6fa";
    ctx.textAlign = "left";
    ctx.fillText(`R2 ${fmt(metric.r2, 3)}`, margin.left + barWidth + 10, y + 18);
  });
}

async function loadReport() {
  const response = await fetch("../results/model_report.json");
  const report = await response.json();

  document.getElementById("recordCount").textContent = `${report.record_count} training rows`;

  document.getElementById("metricCards").innerHTML = Object.entries(report.metrics)
    .map(
      ([target, metric]) => `
        <div class="card">
          <span>${metricLabel[target] || target}</span>
          <strong>R2 ${fmt(metric.r2, 3)}</strong>
          <small>MAE ${fmt(metric.mae, 3)} / RMSE ${fmt(metric.rmse, 3)} / bias ${fmt(metric.bias, 3)}</small>
        </div>
      `,
    )
    .join("");

  document.getElementById("predictionRows").innerHTML = report.top_predictions
    .map(
      (row, index) => `
        <tr>
          <td>${index + 1}</td>
          <td>${fmt(row.power_w, 0)}</td>
          <td>${fmt(row.scan_speed_mm_s, 0)}</td>
          <td>${fmt(row.hatch_spacing_mm, 3)}</td>
          <td>${fmt(row.ultimate_tensile_strength_mpa, 1)}</td>
          <td>${fmt(row.yield_strength_mpa, 1)}</td>
          <td>${fmt(row.elongation_to_fracture_pct, 2)}</td>
          <td>${fmt(row.xct_porosity_pct, 3)}</td>
          <td>${fmt(row.material_performance_score, 1)}</td>
        </tr>
      `,
    )
    .join("");

  document.getElementById("source").innerHTML = `
    <p><strong>${report.source.dataset}</strong></p>
    <p>${report.source.authors}</p>
    <p><a href="${report.source.zenodo}">Zenodo dataset</a> / <a href="${report.source.data_article}">Data article</a></p>
    <p>License: ${report.source.license}</p>
  `;

  drawMetricChart(report.metrics);
}

loadReport().catch((error) => {
  document.body.innerHTML = `<pre>${error.stack}</pre>`;
});
