const API_BASE = '/api';
const USER_HEADER = { 'X-User-Id': 'demo_user' };

let pieChart, barChart;

const labelColors = {
  'Green': '#28a745',
  'Red': '#dc3545',
  'Yellow': '#ffc107'
};

function buildQuery() {
  const label = document.getElementById('filter-label').value.trim();
  const from = document.getElementById('filter-from').value.trim();
  const to = document.getElementById('filter-to').value.trim();
  const p = new URLSearchParams();
  if (label) p.set('label', label);
  if (from) p.set('from', from);
  if (to) p.set('to', to);
  return p.toString();
}

// function setExportHref() {
//   const q = buildQuery();
//   const href = `${API_BASE}/statistics/export${q ? '?' + q : ''}`;
//   document.getElementById('btn-export').href = href; // For CSV Export

//   const pdfHref = `${API_BASE}/statistics/export${q ? '?' + q : ''}&format=pdf`;
//   document.getElementById('btn-export-pdf').href = pdfHref; // For PDF Export
// }

function setExportHref() {
  const q = buildQuery();

  // Set the export link for CSV
  const csvHref = `${API_BASE}/statistics/export${q ? '?' + q : ''}`;
  document.getElementById('btn-export').href = csvHref;

  // Set the export link for PDF
  const pdfHref = `${API_BASE}/statistics/export${q ? '?' + q : ''}&format=pdf`;
  document.getElementById('btn-export-pdf').href = pdfHref;
}

document.getElementById('btn-export-pdf').onclick = async (event) => {
  event.preventDefault(); // Prevent default link click behavior
  
  const q = buildQuery();
  const exportFormat = 'pdf';
  const url = `${API_BASE}/statistics/export?${q ? q + '&' : ''}format=${exportFormat}`;

  try {
    // Fetching the PDF from the server
    const res = await fetch(url, { headers: USER_HEADER });

    // Check for successful response
    if (!res.ok) {
      throw new Error('Failed to fetch PDF');
    }

    const blob = await res.blob(); // Get the response as a Blob (binary data)

    // Create an object URL and trigger the download
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob); // Create an object URL for the Blob
    link.download = `statistics_${new Date().toISOString()}.pdf`; // Set the default file name
    link.click(); // Trigger the download
  } catch (error) {
    console.error('Error while exporting PDF:', error);
  }
};



async function loadStats() {
  const q = buildQuery();
  const res = await fetch(`${API_BASE}/statistics${q ? '?' + q : ''}`, { headers: USER_HEADER });
  const data = await res.json();
  document.getElementById('total-count').textContent = data.total_payloads ?? 0;

  const labels = (data.by_label || []).map(r => r.label);
  const counts = (data.by_label || []).map(r => r.count);
  const colors = labels.map(label => labelColors[label] || '#6c757d');

  // Pie
  const pieCtx = document.getElementById('pieChart');
  if (pieChart) pieChart.destroy();
  pieChart = new Chart(pieCtx, {
    type: 'pie',
    data: {
      labels,
      datasets: [{
        data: counts,
        backgroundColor: colors,
        hoverBackgroundColor: colors
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom' }
      }
    }
  });

  // Bar
  const barCtx = document.getElementById('barChart');
  if (barChart) barChart.destroy();
  barChart = new Chart(barCtx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data: counts,
        label: 'Count',
        backgroundColor: colors,
        borderColor: colors,
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: { beginAtZero: true }
      }
    }
  });


  setExportHref();
}

document.getElementById('btn-apply').onclick = () => loadStats();

window.addEventListener('load', async () => {
  await loadStats();
  setInterval(loadStats, 5000);
});
