// Risk band chart of the decisions page
const rows = JSON.parse(document.getElementById("risk-data").textContent);
const style = getComputedStyle(document.documentElement);
const color = (name) => style.getPropertyValue(name).trim();

Chart.defaults.color = color("--muted");
Chart.defaults.borderColor = color("--line");

new Chart(document.getElementById("risk-chart"), {
  data: {
    labels: rows.map((r) => r.label),
    datasets: [
      { type: "bar", label: "Gerçekleşen gelmeme (%)", data: rows.map((r) => r.rate), backgroundColor: "#e8a25c" },
      {
        type: "line",
        label: "Ortalama tahmin (%)",
        data: rows.map((r) => r.predicted),
        borderColor: "#2f6fdb",
        backgroundColor: "#2f6fdb",
        spanGaps: true,
      },
    ],
  },
  options: {
    animation: false,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    scales: {
      x: { title: { display: true, text: "Tahmini gelmeme riski" } },
      y: { beginAtZero: true, max: 100, title: { display: true, text: "Yüzde" } },
    },
    plugins: {
      tooltip: { callbacks: { footer: (items) => `Randevu: ${rows[items[0].dataIndex].count}` } },
    },
  },
});
