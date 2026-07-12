document.addEventListener('DOMContentLoaded', () => {
        // DOM refs
        const currentGrid = document.getElementById('current-grid');
        const lastUpdated = document.getElementById('last-updated');
        const refreshBtn = document.getElementById('refresh-btn');
        const metricSelect = document.getElementById('metric-select');
        const startDate = document.getElementById('start-date');
        const endDate = document.getElementById('end-date');
        const updateChartBtn = document.getElementById('update-chart-btn');
        const tableBody = document.querySelector('#data-table tbody');
        const tableMetricLabel = document.getElementById('table-metric-label');
        const quickBtns = document.querySelectorAll('.quick-btn');

        let chart = null;
        let allMetrics = new Set();
        let latestData = {};

        // ---------- Helpers ----------
        function formatDate(iso) {
                if (!iso) return '--';
                return new Date(iso).toLocaleString();
        }

        function getMetricLabel(name) {
                // fallback: use name if not found in latest data label
                return latestData.data?.[name]?.label || name;
        }

        // ---------- Current conditions ----------
        async function fetchLatest() {
                try {
                        const res = await fetch('/api/latest');
                        if (!res.ok) throw new Error('No data');
                        const data = await res.json();
                        latestData = data;
                        lastUpdated.textContent = `Last update: ${formatDate(data.created)}`;
                        renderCurrentGrid(data);
                        // Populate metric dropdown if first time
                        if (allMetrics.size === 0) {
                                for (const key of Object.keys(data.data)) {
                                        allMetrics.add(key);
                                }
                                populateMetrics();
                                // Set initial chart after dropdown is ready
                                updateChart();
                        }
                } catch (e) {
                        currentGrid.innerHTML = `<div class="card" style="grid-column:1/-1;">No data yet. Post some readings!</div>`;
                        lastUpdated.textContent = 'Last update: --';
                }
        }

        function renderCurrentGrid(data) {
                const entries = data.data;
                // Define order and grouping
                const order = [
                        { key: 'tempf', label: 'Outdoor Temp' },
                        { key: 'humidity', label: 'Outdoor Humidity' },
                        { key: 'tempinf', label: 'Office Temp' },
                        { key: 'humidityin', label: 'Office Humidity' },
                        { key: 'temp2f', label: 'Bedroom Temp' },
                        { key: 'humidity2', label: 'Bedroom Humidity' },
                        { key: 'baromrelin', label: 'Barometer (rel)' },
                        { key: 'baromabsin', label: 'Barometer (abs)' },
                        { key: 'windspeedmph', label: 'Wind Speed' },
                        { key: 'windgustmph', label: 'Wind Gust' },
                        { key: 'winddir', label: 'Wind Direction' },
                        { key: 'dailyrainin', label: 'Rain (daily)' },
                        { key: 'eventrainin', label: 'Rain (event)' },
                        { key: 'totalrainin', label: 'Rain (total)' },
                        { key: 'solarradiation', label: 'Solar Radiation' },
                        { key: 'uv', label: 'UV Index' },
                        { key: 'battout', label: 'Battery Outdoor' },
                        { key: 'batt2', label: 'Battery Bedroom' },
                ];

                let html = '';
                for (const item of order) {
                        const dp = entries[item.key];
                        if (!dp) continue;
                        let valueHtml = dp.formatted;
                        // Add extra style for some
                        let extraClass = '';
                        if (item.key === 'tempf') extraClass = 'highlight';
                        if (item.key === 'windspeedmph') extraClass = 'wind';
                        html += `<div class="card ${extraClass}">
                        <div class="label">${dp.label}</div>
                        <div class="value">${valueHtml}</div>
                    </div>`;
                }
                currentGrid.innerHTML = html;
        }

        // ---------- Metric dropdown ----------
        function populateMetrics() {
                const current = metricSelect.value;
                metricSelect.innerHTML = '';
                // Sort alphabetically
                const sorted = Array.from(allMetrics).sort();
                for (const m of sorted) {
                        const opt = document.createElement('option');
                        opt.value = m;
                        opt.textContent = getMetricLabel(m);
                        metricSelect.appendChild(opt);
                }
                if (allMetrics.has(current)) metricSelect.value = current;
                else if (sorted.length) metricSelect.value = sorted[0];
        }

        // ---------- Chart & Table ----------
        async function updateChart() {
                const metric = metricSelect.value;
                if (!metric) return;

                const params = new URLSearchParams();
                if (startDate.value) params.append('start', new Date(startDate.value).toISOString());
                if (endDate.value) params.append('end', new Date(endDate.value).toISOString());
                params.append('limit', '500'); // maybe increase for more points

                try {
                        const res = await fetch(`/api/history?${params}`);
                        if (!res.ok) throw new Error('Failed');
                        const entries = await res.json();

                        const labels = [];
                        const values = [];
                        tableBody.innerHTML = '';

                        for (const entry of entries) {
                                const dp = entry.data[metric];
                                if (!dp) continue;
                                const time = new Date(entry.created);
                                labels.push(time.toLocaleString());
                                const num = parseFloat(dp.raw);
                                values.push(isNaN(num) ? 0 : num);

                                const row = tableBody.insertRow();
                                row.insertCell().textContent = time.toLocaleString();
                                row.insertCell().textContent = dp.formatted;
                        }

                        tableMetricLabel.textContent = getMetricLabel(metric);

                        // Render chart
                        if (chart) chart.destroy();
                        const ctx = document.getElementById('chart').getContext('2d');
                        chart = new Chart(ctx, {
                                type: 'line',
                                data: {
                                        labels: labels,
                                        datasets: [{
                                                label: getMetricLabel(metric),
                                                data: values,
                                                borderColor: '#3b82f6',
                                                backgroundColor: 'rgba(59,130,246,0.1)',
                                                fill: true,
                                                tension: 0.2,
                                                pointRadius: 1,
                                        }]
                                },
                                options: {
                                        responsive: true,
                                        maintainAspectRatio: false,
                                        plugins: {
                                                legend: { display: false }
                                        },
                                        scales: {
                                                x: {
                                                        ticks: { maxRotation: 45, autoSkip: true, maxTicksLimit: 20 }
                                                },
                                                y: {
                                                        beginAtZero: false,
                                                }
                                        }
                                }
                        });
                } catch (e) {
                        console.error(e);
                        alert('Error fetching history');
                }
        }

        // ---------- Date presets ----------
        function setDateRange(days) {
                const end = new Date();
                const start = new Date(end);
                start.setDate(start.getDate() - days);
                startDate.value = start.toISOString().slice(0, 16);
                endDate.value = end.toISOString().slice(0, 16);
                updateChart();
        }

        // ---------- Auto-refresh ----------
        let refreshInterval = null;
        function startAutoRefresh() {
                if (refreshInterval) clearInterval(refreshInterval);
                refreshInterval = setInterval(fetchLatest, 60000); // every minute
        }

        async function fetchDailyStats() {
                try {
                        const res = await fetch('/api/daily_stats');
                        if (!res.ok) throw new Error('No daily stats');
                        const stats = await res.json();

                        const grid = document.getElementById('current-grid');

                        // High temp card (highlighted)
                        const maxCard = document.createElement('div');
                        maxCard.className = 'card highlight';
                        maxCard.innerHTML = `<div class="label">🔥 Today's High</div>
                                     <div class="value">${stats.max}°F</div>`;
                        grid.prepend(maxCard);

                        // Low temp card
                        const minCard = document.createElement('div');
                        minCard.className = 'card';
                        minCard.innerHTML = `<div class="label">❄️ Today's Low</div>
                                     <div class="value">${stats.min}°F</div>`;
                        grid.prepend(minCard);

                } catch (e) {
                        console.log('Daily stats not available yet.');
                }
        }

        // ---------- Init ----------
        async function init() {
                await fetchLatest();
                await fetchDailyStats();
                // If we have metrics, set default date range (last 7 days) and load chart
                if (allMetrics.size > 0) {
                        // Set default to last 7 days
                        const end = new Date();
                        const start = new Date(end);
                        start.setDate(start.getDate() - 7);
                        startDate.value = start.toISOString().slice(0, 16);
                        endDate.value = end.toISOString().slice(0, 16);
                        updateChart();
                }
                startAutoRefresh();

                // Event listeners
                refreshBtn.addEventListener('click', () => { fetchLatest(); });
                updateChartBtn.addEventListener('click', updateChart);
                quickBtns.forEach(btn => {
                        btn.addEventListener('click', () => {
                                const days = parseInt(btn.dataset.days, 10);
                                setDateRange(days);
                        });
                });
                // When metric changes, we could auto-update, but user clicks "Update Chart"
                // Optionally, we can auto-update on change:
                // metricSelect.addEventListener('change', updateChart);
        }

        init();
});

