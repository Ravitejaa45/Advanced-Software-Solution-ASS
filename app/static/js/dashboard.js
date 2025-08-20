const API_BASE = "/api";
const USER_HEADER = { "X-User-Id": "demo_user" };

let pieChart, barChart;

const labelColors = {
  Green: "#28a745",
  Red: "#dc3545",
  Yellow: "#ffc107",
};

const socket = io("/", {
  path: "/socket.io",
  transports: ["websocket", "polling"],
  upgrade: true,
});

socket.on("connect", () => {
  console.log("WebSocket Connected!");
});

function updateStats(stats) {
  document.getElementById("total-count").textContent =
    stats.total_payloads ?? 0;

  console.log("stats", stats);

  const labels = stats.by_label.map((r) => r.label);
  const counts = stats.by_label.map((r) => r.count);
  const colors = labels.map((label) => labelColors[label] || "#6c757d");

  const pieCtx = document.getElementById("pieChart");
  if (pieChart) pieChart.destroy();
  pieChart = new Chart(pieCtx, {
    type: "pie",
    data: {
      labels,
      datasets: [
        {
          data: counts,
          backgroundColor: colors,
          hoverBackgroundColor: colors,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom" },
      },
    },
  });

  const barCtx = document.getElementById("barChart");
  if (barChart) barChart.destroy();
  barChart = new Chart(barCtx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: counts,
          label: "Count",
          backgroundColor: colors,
          borderColor: colors,
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: { beginAtZero: true },
      },
    },
  });
}

socket.on("stats_update", function (stats) {
  updateStats(stats);
});

function setExportHref() {
  const q = buildQuery();

  const csvHref = `${API_BASE}/statistics/export${q ? "?" + q : ""}`;
  document.getElementById("btn-export").href = csvHref;

  // const pdfHref = `${API_BASE}/statistics/export${
  //   q ? "?" + q + "&" : "?"
  // }format=pdf`;
  // // document.getElementById('btn-export-pdf').href = pdfHref;
}

document.getElementById("btn-apply").onclick = () => loadStats();

window.addEventListener("load", async () => {
  await loadStats();
});

function buildQuery() {
  const label = document.getElementById("filter-label").value.trim();
  const from = document.getElementById("filter-from").value.trim();
  const to = document.getElementById("filter-to").value.trim();
  const p = new URLSearchParams();
  if (label) p.set("label", label);
  if (from) p.set("from", from);
  if (to) p.set("to", to);
  return p.toString();
}

async function loadStats() {
  const q = buildQuery();
  const res = await fetch(`${API_BASE}/statistics${q ? "?" + q : ""}`, {
    headers: USER_HEADER,
  });
  const data = await res.json();
  document.getElementById("total-count").textContent = data.total_payloads ?? 0;

  const labels = (data.by_label || []).map((r) => r.label);
  const counts = (data.by_label || []).map((r) => r.count);
  const colors = labels.map((label) => labelColors[label] || "#6c757d");

  const pieCtx = document.getElementById("pieChart");
  if (pieChart) pieChart.destroy();
  pieChart = new Chart(pieCtx, {
    type: "pie",
    data: {
      labels,
      datasets: [
        {
          data: counts,
          backgroundColor: colors,
          hoverBackgroundColor: colors,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom" },
      },
    },
  });

  const barCtx = document.getElementById("barChart");
  if (barChart) barChart.destroy();
  barChart = new Chart(barCtx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: counts,
          label: "Count",
          backgroundColor: colors,
          borderColor: colors,
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: { beginAtZero: true },
      },
    },
  });

  setExportHref();
}
