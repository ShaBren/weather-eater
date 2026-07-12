document.addEventListener('DOMContentLoaded', () => {
    const metricSelect = document.getElementById('metric-select');
    const startDate = document.getElementById('start-date');
    const endDate = document.getElementById('end-date');
    const updateBtn = document.getElementById('update-btn');
    const latestDiv = document.getElementById('latest');
    const tableBody = document.querySelector('#data-table tbody');
    const tableMetricLabel = document.getElementById('table-metric-label');

    let chart = null;
    let allMetrics = new Set();

    // Fetch latest data and populate metric dropdown
    async function fetchLatest() {
        try {
            const res = await fetch('/api/latest');
            if (!res.ok) throw new Error('No data');
            const data = await res.json();
            // Display latest
            latestDiv.innerHTML = `<div style="grid-column:1/-1; font-weight:bold;">Latest reading: ${new Date(data.created).toLocaleString()}</div>`;
            for (const [key, val] of Object.entries(data.data)) {
                allMetrics.add(key);
                const div = document.createElement('div');
                div.className = 'latest-item';
                div.innerHTML = `<strong>${val.label}</strong><span>${val.formatted}</span>`;
                latestDiv.appendChild(div);
            }
            populateMetrics();
        } catch (e) {
            latestDiv.innerHTML = '<p>No data yet.</p>';
        }
    }

    function populateMetrics() {
        const current = metricSelect.value;
        metricSelect.innerHTML = '';
        for (const m of allMetrics) {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = m;
            metricSelect.appendChild(opt);
        }
        if (allMetrics.has(current)) metricSelect.value = current;
        else metricSelect.value = allMetrics.values().next().value || '';
    }

    // Fetch history and render chart/table
    async function updateChart() {
        const metric = metricSelect.value;
        if (!metric) return;

        const params = new URLSearchParams();
        if (startDate.value) params.append('start', new Date(startDate.value).toISOString());
        if (endDate.value) params.append('end', new Date(endDate.value).toISOString());
        params.append('limit', '500'); // adjust as needed

        try {
            const res = await fetch(`/api/history?${params}`);
            if (!res.ok) throw new Error('Failed to fetch history');
            const entries = await res.json();

            // Prepare data for chart and table
            const labels = [];
            const values = [];
            tableBody.innerHTML = '';

            for (const entry of entries) {
                const dataPoint = entry.data[metric];
                if (!dataPoint) continue;
                const time = new Date(entry.created);
                labels.push(time.toLocaleString());
                values.push(parseFloat(dataPoint.raw) || 0);

                const row = tableBody.insertRow();
                row.insertCell().textContent = time.toLocaleString();
                row.insertCell().textContent = dataPoint.formatted;
            }

            // Update table header
            tableMetricLabel.textContent = metric;

            // Render chart
            if (chart) chart.destroy();
            const ctx = document.getElementById('chart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: metric,
                        data: values,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52,152,219,0.1)',
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: { ticks: { maxRotation: 45 } }
                    }
                }
            });
        } catch (e) {
            console.error(e);
            alert('Error fetching history');
        }
    }

    // Set default date range (last 7 days)
    function setDefaultDates() {
        const now = new Date();
        const sevenDaysAgo = new Date(now);
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        startDate.value = sevenDaysAgo.toISOString().slice(0,16);
        endDate.value = now.toISOString().slice(0,16);
    }

    updateBtn.addEventListener('click', updateChart);

    // Initial load
    setDefaultDates();
    fetchLatest().then(() => {
        // If metrics loaded, update chart automatically
        if (metricSelect.value) updateChart();
    });
});
