document.addEventListener('DOMContentLoaded', () => {

    // ---------- Constants ----------
    const CACHE_KEY = 'weather_metrics_cache';
    const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours
    const CHART_SETTINGS_KEY = 'weather_chart_settings';
    const DASHBOARD_SETTINGS_KEY = 'weather_dashboard_settings';

    // ---------- DOM refs ----------
    const currentGrid = document.getElementById('current-grid');
    const lastUpdated = document.getElementById('last-updated');
    const refreshBtn = document.getElementById('refresh-btn');
    const settingsBtn = document.getElementById('settings-btn');
    const closeSettingsBtn = document.getElementById('close-settings-btn');
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    const settingsModal = document.getElementById('settings-modal');
    const settingsList = document.getElementById('settings-list');
    const metricSelect = document.getElementById('metric-select');
    const startDate = document.getElementById('start-date');
    const endDate = document.getElementById('end-date');
    const updateChartBtn = document.getElementById('update-chart-btn');
    const tableBody = document.querySelector('#data-table tbody');
    const tableMetricLabel = document.getElementById('table-metric-label');
    const quickBtns = document.querySelectorAll('.quick-btn');
    const chartLoading = document.getElementById('chart-loading');

    // ---------- State ----------
    let chart = null;
    let refreshInterval = null;
    let latestData = null;
    let dailyStats = null;
    let allMetrics = [];
    let cardRegistry = [];
    let enabledCardIds = new Set();
    let cardOrder = [];
    let settingsLoaded = false; // track if we loaded saved settings
    let choicesInstance = null;

    // ---------- API ----------
    const API = {
        async getMetrics() {
            const res = await fetch('/api/metrics');
            if (!res.ok) throw new Error('Failed to fetch metrics');
            return res.json();
        },
        async getLatest() {
            const res = await fetch('/api/latest');
            if (!res.ok) throw new Error('No latest data');
            return res.json();
        },
        async getDailyStats() {
            const res = await fetch('/api/daily_stats');
            if (!res.ok) throw new Error('No daily stats');
            return res.json();
        },
        async getHistory(params) {
            const qs = new URLSearchParams(params).toString();
            const res = await fetch(`/api/history?${qs}`);
            if (!res.ok) throw new Error('Failed to fetch history');
            return res.json();
        }
    };

    // ---------- Settings (Dashboard) ----------
    function loadDashboardSettings() {
        try {
            const stored = JSON.parse(localStorage.getItem(DASHBOARD_SETTINGS_KEY));
            if (stored) {
                if (Array.isArray(stored.enabled)) {
                    enabledCardIds = new Set(stored.enabled);
                    settingsLoaded = true;
                }
                if (Array.isArray(stored.order)) cardOrder = stored.order;
                return;
            }
        } catch (e) { /* ignore */ }
        enabledCardIds = new Set();
        cardOrder = [];
        settingsLoaded = false;
    }

    function saveDashboardSettings() {
        localStorage.setItem(DASHBOARD_SETTINGS_KEY, JSON.stringify({
            enabled: Array.from(enabledCardIds),
            order: cardOrder
        }));
    }

    // ---------- Metrics Cache ----------
    function loadMetricsCache() {
        try {
            const cached = JSON.parse(localStorage.getItem(CACHE_KEY));
            if (cached && cached.timestamp && (Date.now() - cached.timestamp < CACHE_TTL)) {
                return cached.metrics;
            }
        } catch (e) { /* ignore */ }
        return null;
    }

    function saveMetricsCache(metrics) {
        localStorage.setItem(CACHE_KEY, JSON.stringify({
            timestamp: Date.now(),
            metrics: metrics
        }));
    }

    // ---------- Chart Settings ----------
    function loadChartSettings() {
        try {
            const stored = JSON.parse(localStorage.getItem(CHART_SETTINGS_KEY));
            if (stored) {
                return stored;
            }
        } catch (e) { /* ignore */ }
        return null;
    }

    function saveChartSettings() {
        // Get currently selected values from Choices
        const selected = choicesInstance ? choicesInstance.getValue(true) : [];
        localStorage.setItem(CHART_SETTINGS_KEY, JSON.stringify({
            selected: selected,
            start: startDate.value,
            end: endDate.value,
            limit: 500
        }));
    }

    // ---------- Card Registry Builder ----------
    function buildCardRegistry(metrics) {
        const findMetric = (id) => metrics.find(m => m.id === id);
        const registry = [];

        // Daily Extremes
        registry.push({
            id: 'daily_extremes',
            label: 'Daily Extremes',
            icon: '📈',
            priority: 0,
            defaultEnabled: true,
            render: function(data, stats) {
                if (!stats || stats.min === undefined || stats.max === undefined) return null;
                return `<div class="label">${this.icon} ${this.label} (observed)</div>
                        <div class="value">${stats.max}°F <span style="font-size:0.7rem;font-weight:400;color:#94a3b8;">high</span></div>
                        <div class="value" style="font-size:1.2rem;">${stats.min}°F <span style="font-size:0.7rem;font-weight:400;color:#94a3b8;">low</span></div>`;
            }
        });

        // Outdoor Temp with Feels Like
        const tempOut = findMetric('tempf');
        if (tempOut) {
            registry.push({
                id: 'outdoor_temp',
                label: 'Outdoor Temp',
                icon: '🌡️',
                priority: 1,
                defaultEnabled: true,
                render: function(data, stats) {
                    const dp = data.data['tempf'];
                    if (!dp) return null;
                    let feelsLikeHtml = '';
                    const t = parseFloat(dp.raw);
                    const rh = data.data['humidity'] ? parseFloat(data.data['humidity'].raw) : null;
                    if (rh !== null && t >= 80 && rh >= 40) {
                        const hi = calculateHeatIndex(t, rh);
                        if (hi !== null && hi > t) {
                            feelsLikeHtml = `<div class="sub">Feels like ${hi.toFixed(1)}°F</div>`;
                        }
                    }
                    return `<div class="label">${this.icon} ${this.label}</div>
                            <div class="value">${dp.formatted}</div>
                            ${feelsLikeHtml}`;
                }
            });
        }

        // Regular metric cards (skip tempf)
        const skipIds = new Set(['tempf']);
        const metricCards = metrics
            .filter(m => !skipIds.has(m.id))
            .map((m, idx) => ({
                id: m.id,
                label: m.label,
                icon: getIconForMetric(m.id),
                priority: 10 + idx,
                defaultEnabled: true,
                render: function(data, stats) {
                    const dp = data.data[this.id];
                    if (!dp) return null;
                    return `<div class="label">${this.icon} ${this.label}</div>
                            <div class="value">${dp.formatted}</div>`;
                }
            }));

        registry.push(...metricCards);

        // Apply enabled/order only if settings were loaded
        if (!settingsLoaded) {
            // First run: enable all cards with defaultEnabled, set order by priority
            registry.forEach(card => {
                if (card.defaultEnabled !== false) enabledCardIds.add(card.id);
                if (!cardOrder.includes(card.id)) cardOrder.push(card.id);
            });
        } else {
            // Merge: add any new cards (not in enabled) with defaultEnabled
            registry.forEach(card => {
                if (!enabledCardIds.has(card.id) && card.defaultEnabled !== false) {
                    enabledCardIds.add(card.id);
                }
                if (!cardOrder.includes(card.id)) {
                    cardOrder.push(card.id);
                }
            });
        }

        // Ensure order is up-to-date (remove any stale IDs)
        const validIds = new Set(registry.map(c => c.id));
        cardOrder = cardOrder.filter(id => validIds.has(id));

        return registry;
    }

    function getIconForMetric(id) {
        const map = {
            'humidity': '💧', 'humidityin': '💧', 'humidity2': '💧',
            'tempinf': '🌡️', 'temp2f': '🌡️',
            'baromrelin': '📊', 'baromabsin': '📊',
            'windspeedmph': '💨', 'windgustmph': '💨', 'winddir': '🧭',
            'dailyrainin': '☔', 'eventrainin': '☔', 'totalrainin': '☔', 'monthlyrainin': '☔', 'weeklyrainin': '☔', 'hourlyrainin': '☔',
            'solarradiation': '☀️', 'uv': '☀️',
            'battout': '🔋', 'batt2': '🔋', 'batt_co2': '🔋',
            'heat_index': '🌡️',
        };
        return map[id] || '📌';
    }

    // ---------- Heat Index ----------
    function calculateHeatIndex(tempF, humidityPercent) {
        if (humidityPercent < 40) return tempF;
        const T = tempF, R = humidityPercent;
		if (tempF < 80) {
			const HI = 0.5 * (0.5 * (T + 61.0 + ((T - 68.0) * 1.2) + (R * 0.094)) + T);
        	return Math.round(HI * 10) / 10;
		}
		else {
			const HI = -42.379 + 2.04901523*T + 10.14333127*R - 0.22475541*T*R
					 - 0.00683783*T*T - 0.05481717*R*R + 0.00122874*T*T*R
					 + 0.00085282*T*R*R - 0.00000199*T*T*R*R;
        	if (HI < 80) return tempF;
        	return Math.round(HI * 10) / 10;
		}
    }

    // ---------- Render Dashboard ----------
    function renderDashboard() {
        if (!latestData) {
            currentGrid.innerHTML = `<div class="card" style="grid-column:1/-1;">No data yet.</div>`;
            return;
        }

        const sorted = [...cardRegistry].sort((a, b) => {
            const idxA = cardOrder.indexOf(a.id);
            const idxB = cardOrder.indexOf(b.id);
            if (idxA === -1 && idxB === -1) return a.priority - b.priority;
            if (idxA === -1) return 1;
            if (idxB === -1) return -1;
            return idxA - idxB;
        });

        let html = '';
        let renderedCount = 0;

        for (const card of sorted) {
            if (!enabledCardIds.has(card.id)) continue;
            const cardHtml = card.render.call(card, latestData, dailyStats);
            if (cardHtml) {
                html += `<div class="card">${cardHtml}</div>`;
                renderedCount++;
            }
        }

        if (renderedCount === 0) {
            html = `<div class="card" style="grid-column:1/-1;">No cards enabled. Go to ⚙️ settings to turn some on.</div>`;
        }

        currentGrid.innerHTML = html;
        lastUpdated.textContent = `Last update: ${formatDate(latestData.created)}`;
    }

    function formatDate(iso) {
        if (!iso) return '--';
        return new Date(iso).toLocaleString();
    }

    // ---------- Fetch & Refresh ----------
    async function refreshAll() {
        try {
            const [latest, stats] = await Promise.all([
                API.getLatest(),
                API.getDailyStats().catch(() => null)
            ]);
            latestData = latest;
            dailyStats = stats;
            renderDashboard();
        } catch (e) {
            console.warn('Refresh failed:', e);
        }
    }

    // ---------- Settings Panel ----------
    function renderSettingsPanel() {
        let html = '';
        const sorted = [...cardRegistry].sort((a, b) => {
            const idxA = cardOrder.indexOf(a.id);
            const idxB = cardOrder.indexOf(b.id);
            if (idxA === -1 && idxB === -1) return a.priority - b.priority;
            if (idxA === -1) return 1;
            if (idxB === -1) return -1;
            return idxA - idxB;
        });

        for (const card of sorted) {
            const checked = enabledCardIds.has(card.id) ? 'checked' : '';
            html += `
                <div class="toggle-item" data-card-id="${card.id}">
                    <div>
                        <label for="toggle-${card.id}">${card.icon || '📌'} ${card.label}</label>
                        <div class="card-preview">ID: ${card.id}</div>
                    </div>
                    <div class="switch">
                        <input type="checkbox" id="toggle-${card.id}" ${checked} data-card-id="${card.id}">
                        <span class="slider"></span>
                    </div>
                </div>
            `;
        }
        settingsList.innerHTML = html;

        // Auto-save on toggle
        settingsList.querySelectorAll('input[type="checkbox"]').forEach(input => {
            input.addEventListener('change', (e) => {
                const id = e.target.dataset.cardId;
                if (e.target.checked) {
                    enabledCardIds.add(id);
                } else {
                    enabledCardIds.delete(id);
                }
                saveDashboardSettings();
                renderDashboard();
            });
        });

        if (window.Sortable) {
            new Sortable(settingsList, {
                animation: 150,
                handle: '.toggle-item',
                ghostClass: 'sortable-ghost',
                onEnd: function() {
                    const items = settingsList.querySelectorAll('.toggle-item');
                    cardOrder = Array.from(items).map(el => el.dataset.cardId);
                    saveDashboardSettings();
                    renderDashboard();
                }
            });
        }
    }

    function openSettings() {
        renderSettingsPanel();
        settingsModal.classList.add('visible');
    }

    function closeSettings() {
        settingsModal.classList.remove('visible');
    }

    function saveAndCloseSettings() {
        saveDashboardSettings();
        renderDashboard();
        closeSettings();
    }

    // ---------- Chart ----------
    function getChartColors(isDark) {
        return {
            gridColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            tickColor: isDark ? '#94a3b8' : '#475569',
            labelColor: isDark ? '#e2e8f0' : '#1e293b',
            tooltipBackground: isDark ? '#1e293b' : 'white',
            tooltipBorder: isDark ? '#334155' : '#cbd5e1',
            tooltipText: isDark ? '#e2e8f0' : '#1e293b',
        };
    }

    async function updateChart() {
        const selected = choicesInstance ? choicesInstance.getValue(true) : [];
        if (selected.length === 0) {
            alert('Please select at least one metric.');
            return;
        }

        const params = {
            limit: 500
        };
        if (startDate.value) params.start = new Date(startDate.value).toISOString();
        if (endDate.value) params.end = new Date(endDate.value).toISOString();

        chartLoading.style.display = 'flex';

        try {
            let entries = await API.getHistory(params);
            entries.reverse(); // oldest first

            const datasets = [];
            const labels = [];
            const unitMap = {};

            for (const metricId of selected) {
                const metric = allMetrics.find(m => m.id === metricId);
                if (!metric) continue;

                let dataPoints = [];

                if (metricId === 'heat_index') {
                    dataPoints = entries.map(e => {
                        const tempRaw = e.data['tempf']?.raw;
                        const humRaw = e.data['humidity']?.raw;
                        if (!tempRaw || !humRaw) return null;
                        const t = parseFloat(tempRaw);
                        const h = parseFloat(humRaw);
                        if (isNaN(t) || isNaN(h)) return null;
                        const hi = calculateHeatIndex(t, h);
                        if (hi === null) return null;
                        return { time: new Date(e.created), value: hi };
                    }).filter(d => d !== null);
                } else {
                    dataPoints = entries.map(e => {
                        const dp = e.data[metricId];
                        if (!dp) return null;
                        return { time: new Date(e.created), value: parseFloat(dp.raw) };
                    }).filter(d => d !== null);
                }

                if (dataPoints.length === 0) continue;

                const unit = metric.units || 'value';
                const color = getColorForMetric(datasets.length);

                let yAxisID = 'y';
                const existingUnits = Object.values(unitMap);
                if (existingUnits.length > 0 && !existingUnits.includes(unit)) {
                    yAxisID = 'y1';
                }
                unitMap[metricId] = unit;

                datasets.push({
                    label: metric.label,
                    data: dataPoints.map(d => d.value),
                    borderColor: color,
                    backgroundColor: color + '33',
                    fill: true,
                    tension: 0.2,
                    pointRadius: 1,
                    yAxisID: yAxisID,
                });

                if (labels.length === 0) {
                    labels.push(...dataPoints.map(d => d.time.toLocaleString()));
                }
            }

            // Table
            const firstMetric = selected[0];
            const firstMetricLabel = allMetrics.find(m => m.id === firstMetric)?.label || firstMetric;
            tableMetricLabel.textContent = firstMetricLabel;
            tableBody.innerHTML = '';
            for (const entry of entries) {
                let displayValue = '--';
                if (firstMetric === 'heat_index') {
                    const t = entry.data['tempf']?.raw;
                    const h = entry.data['humidity']?.raw;
                    if (t && h) {
                        const hi = calculateHeatIndex(parseFloat(t), parseFloat(h));
                        if (hi !== null) displayValue = hi.toFixed(1) + '°F';
                    }
                } else {
                    const dp = entry.data[firstMetric];
                    if (dp) displayValue = dp.formatted;
                }
                const row = tableBody.insertRow();
                row.insertCell().textContent = new Date(entry.created).toLocaleString();
                row.insertCell().textContent = displayValue;
            }

            if (chart) chart.destroy();

            const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const colors = getChartColors(isDark);

            const ctx = document.getElementById('chart').getContext('2d');
            const chartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { color: colors.labelColor }
                    },
                    tooltip: {
                        backgroundColor: colors.tooltipBackground,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 1,
                        titleColor: colors.tooltipText,
                        bodyColor: colors.tooltipText,
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: colors.tickColor,
                            maxRotation: 45,
                            autoSkip: true,
                            maxTicksLimit: 20
                        },
                        grid: { color: colors.gridColor }
                    }
                }
            };

            const yAxes = {};
            const units = Object.values(unitMap);
            if (units.length > 1) {
                const firstUnit = units[0];
                const secondUnit = units[1];
                yAxes['y'] = {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: firstUnit, color: colors.tickColor },
                    ticks: { color: colors.tickColor },
                    grid: { color: colors.gridColor }
                };
                yAxes['y1'] = {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { display: true, text: secondUnit, color: colors.tickColor },
                    ticks: { color: colors.tickColor },
                    grid: { drawOnChartArea: false }
                };
                datasets.forEach(ds => {
                    const m = allMetrics.find(m => m.id === ds.label);
                    if (m && m.units === firstUnit) ds.yAxisID = 'y';
                    else if (m && m.units === secondUnit) ds.yAxisID = 'y1';
                });
            } else if (units.length === 1) {
                yAxes['y'] = {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: units[0], color: colors.tickColor },
                    ticks: { color: colors.tickColor },
                    grid: { color: colors.gridColor }
                };
            }

            chartOptions.scales = { ...chartOptions.scales, ...yAxes };
            chart = new Chart(ctx, {
                type: 'line',
                data: { labels, datasets },
                options: chartOptions
            });

            // Save chart settings
            saveChartSettings();

        } catch (e) {
            console.error(e);
            alert('Error fetching history');
        } finally {
            chartLoading.style.display = 'none';
        }
    }

    function getColorForMetric(index) {
        const colors = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];
        return colors[index % colors.length];
    }

    // ---------- Date helpers ----------
    function localDateTimeString(date) {
        const pad = n => String(n).padStart(2, '0');
        return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
    }

    function setDateRange(hours) {
        const end = new Date();
        const start = new Date(end);
        start.setHours(start.getHours() - hours);
        startDate.value = localDateTimeString(start);
        endDate.value = localDateTimeString(end);
        updateChart();
    }

    // ---------- Auto-refresh ----------
    function startAutoRefresh() {
        if (refreshInterval) clearInterval(refreshInterval);
        refreshInterval = setInterval(refreshAll, 30000);
    }

    // ---------- Initialize Choices ----------
    function initChoices(selectedIds) {
        if (choicesInstance) {
            choicesInstance.destroy();
        }
        const choices = new Choices(metricSelect, {
            removeItemButton: true,
            searchEnabled: true,
            placeholder: true,
            placeholderValue: 'Select metrics...',
            shouldSort: false,
        });
        choicesInstance = choices;

        // Populate options
        const sorted = [...allMetrics].sort((a, b) => a.label.localeCompare(b.label));
        choices.clearStore();
        sorted.forEach(m => {
            choices.setChoices([{ value: m.id, label: m.label, selected: selectedIds.includes(m.id) }], 'value', 'label', true);
        });

        // Save on change
        metricSelect.addEventListener('change', () => {
            saveChartSettings();
        });
    }

    // ---------- Build UI after metrics are set ----------
    function buildUI(selectedIds) {
        cardRegistry = buildCardRegistry(allMetrics);
        saveDashboardSettings();

        // Initialize choices
        initChoices(selectedIds);

        // Set chart controls
        const chartSettings = loadChartSettings();
        if (chartSettings) {
            if (chartSettings.start) startDate.value = chartSettings.start;
            if (chartSettings.end) endDate.value = chartSettings.end;
        } else {
            // default: last 24h
            const end = new Date();
            const start = new Date(end);
            start.setHours(start.getHours() - 24);
            startDate.value = localDateTimeString(start);
            endDate.value = localDateTimeString(end);
        }

        // Load initial data and chart
        refreshAll().then(() => {
            updateChart();
        });
        startAutoRefresh();
    }

    // ---------- Init ----------
    async function init() {
        // 1. Load dashboard settings
        loadDashboardSettings();

        // 2. Load metrics from cache first (instant)
        let selectedIds = ['tempf', 'humidity']; // default
        const cachedMetrics = loadMetricsCache();
        if (cachedMetrics) {
            allMetrics = cachedMetrics;
            if (!allMetrics.find(m => m.id === 'heat_index')) {
                allMetrics.push({ id: 'heat_index', label: 'Heat Index (Feels Like)', units: '°F' });
            }
            // Load chart settings to get selected IDs
            const chartSettings = loadChartSettings();
            if (chartSettings && chartSettings.selected && chartSettings.selected.length) {
                selectedIds = chartSettings.selected;
            }
            buildUI(selectedIds);
        }

        // 3. Fetch fresh metrics in background
        try {
            const freshMetrics = await API.getMetrics();
            // Add virtual metric
            if (!freshMetrics.find(m => m.id === 'heat_index')) {
                freshMetrics.push({ id: 'heat_index', label: 'Heat Index (Feels Like)', units: '°F' });
            }
            // Only update if different
            const oldIds = new Set(allMetrics.map(m => m.id));
            const newIds = new Set(freshMetrics.map(m => m.id));
            if (oldIds.size !== newIds.size || ![...oldIds].every(id => newIds.has(id))) {
                allMetrics = freshMetrics;
                saveMetricsCache(freshMetrics);
                // Rebuild UI with current selections preserved
                const currentSelected = choicesInstance ? choicesInstance.getValue(true) : selectedIds;
                // Destroy old choices and rebuild
                if (choicesInstance) choicesInstance.destroy();
                buildUI(currentSelected);
            } else {
                // Just update cache if same
                saveMetricsCache(freshMetrics);
            }
        } catch (e) {
            console.warn('Could not fetch metrics, using cached.');
            if (!cachedMetrics) {
                // Fallback
                allMetrics = [
                    { id: 'tempf', label: 'Outdoor Temp', units: '°F' },
                    { id: 'humidity', label: 'Outdoor Humidity', units: '%' },
                    { id: 'heat_index', label: 'Heat Index (Feels Like)', units: '°F' }
                ];
                buildUI(['tempf', 'humidity']);
            }
        }

        // ---------- Event Listeners ----------
        refreshBtn.addEventListener('click', refreshAll);
        settingsBtn.addEventListener('click', openSettings);
        closeSettingsBtn.addEventListener('click', closeSettings);
        saveSettingsBtn.addEventListener('click', saveAndCloseSettings);
        settingsModal.addEventListener('click', (e) => {
            if (e.target === settingsModal) closeSettings();
        });
        updateChartBtn.addEventListener('click', updateChart);
        quickBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const hours = parseInt(btn.dataset.hours, 10);
                setDateRange(hours);
            });
        });

        // Listen for dark mode changes to re-render chart
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
            if (chart) updateChart();
        });
    }

    init();
});
