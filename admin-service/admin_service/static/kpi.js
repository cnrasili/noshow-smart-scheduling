// Daily KPI chart of the schedule KPI page
const rows = JSON.parse(document.getElementById("kpi-data").textContent);
const style = getComputedStyle(document.documentElement);
const color = (name) => style.getPropertyValue(name).trim();

Chart.defaults.color = color("--muted");
Chart.defaults.borderColor = color("--line");

new Chart(document.getElementById("kpi-chart"), {
  data: {
    labels: rows.map((r) => r.date),
    datasets: [
      { type: "bar", label: "Boş süre (dk)", data: rows.map((r) => r.idle), backgroundColor: "#8fb3ee", yAxisID: "minutes" },
      { type: "bar", label: "Fazla mesai (dk)", data: rows.map((r) => r.overtime), backgroundColor: "#e8a25c", yAxisID: "minutes" },
      {
        type: "line",
        label: "Doluluk (%)",
        data: rows.map((r) => r.utilization),
        borderColor: "#2f9e6e",
        backgroundColor: "#2f9e6e",
        yAxisID: "percent",
      },
    ],
  },
  options: {
    animation: false,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    scales: {
      minutes: { position: "left", beginAtZero: true, title: { display: true, text: "Dakika" } },
      percent: { position: "right", beginAtZero: true, grid: { drawOnChartArea: false }, title: { display: true, text: "Doluluk (%)" } },
    },
  },
});
