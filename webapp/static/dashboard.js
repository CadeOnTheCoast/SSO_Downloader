(function () {
  const state = {
    timeSeriesChart: null,
    utilityChart: null,
  };

  function setStatus(message, isError = false) {
    const el = document.getElementById('status');
    if (!el) return;
    el.textContent = message || '';
    el.style.color = isError ? '#b91c1c' : '#374151';
  }

  function formatNumber(value) {
    if (value === null || value === undefined) return '–';
    if (isNaN(value)) return String(value);
    return Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });
  }

  function buildQueryParams() {
    const params = new URLSearchParams();
    const utility = document.getElementById('utility-select').value;
    const county = document.getElementById('county-select').value;
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const limit = document.getElementById('record-limit').value;

    if (utility) params.set('utility_id', utility);
    if (county) params.set('county', county);
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    if (limit) params.set('limit', limit);
    return params;
  }

  function ensureFilters(params) {
    return (
      params.has('utility_id') ||
      params.has('county') ||
      params.has('start_date') ||
      params.has('end_date')
    );
  }

  async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Request failed (${response.status})`);
    }
    return response.json();
  }

  async function loadFilters() {
    try {
      const data = await fetchJson('/filters');
      const utilitySelect = document.getElementById('utility-select');
      const countySelect = document.getElementById('county-select');

      (data.utilities || []).forEach((item) => {
        const option = document.createElement('option');
        option.value = item.id;
        option.textContent = `${item.name} (${item.id})`;
        utilitySelect.appendChild(option);
      });

      (data.counties || []).forEach((name) => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        countySelect.appendChild(option);
      });
    } catch (err) {
      setStatus('Unable to load filters.', true);
    }
  }

  function setDefaultDates() {
    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - 6);
    document.getElementById('end-date').value = end.toISOString().slice(0, 10);
    document.getElementById('start-date').value = start.toISOString().slice(0, 10);
  }

  function renderSummary(data) {
    const overall = data.overall || {};
    document.getElementById('summary-total-count').textContent = formatNumber(
      overall.count
    );
    document.getElementById('summary-total-volume').textContent = formatNumber(
      overall.total_volume_gallons
    );
    document.getElementById('summary-avg-volume').textContent = formatNumber(
      overall.mean_volume_gallons
    );
    document.getElementById('summary-max-volume').textContent = formatNumber(
      overall.max_volume_gallons
    );
  }

  function renderTimeSeries(points) {
    const ctx = document.getElementById('time-series-chart');
    if (!ctx) return;
    const labels = points.map((p) => p.date);
    const counts = points.map((p) => p.count);
    const volumes = points.map((p) => p.total_volume_gallons);

    if (state.timeSeriesChart) {
      state.timeSeriesChart.data.labels = labels;
      state.timeSeriesChart.data.datasets[0].data = counts;
      state.timeSeriesChart.data.datasets[1].data = volumes;
      state.timeSeriesChart.update();
      return;
    }

    state.timeSeriesChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Spills',
            data: counts,
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37,99,235,0.1)',
            tension: 0.2,
            yAxisID: 'y',
          },
          {
            label: 'Total volume (gal)',
            data: volumes,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16,185,129,0.1)',
            tension: 0.2,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        scales: {
          y: {
            position: 'left',
            title: { display: true, text: 'Spills' },
          },
          y1: {
            position: 'right',
            grid: { drawOnChartArea: false },
            title: { display: true, text: 'Volume (gal)' },
          },
        },
        plugins: {
          legend: { position: 'bottom' },
        },
      },
    });
  }

  function renderUtilityBars(bars) {
    const ctx = document.getElementById('utility-chart');
    if (!ctx) return;
    const labels = bars.map((b) => b.label);
    const volumes = bars.map((b) => b.total_volume_gallons);

    if (state.utilityChart) {
      state.utilityChart.data.labels = labels;
      state.utilityChart.data.datasets[0].data = volumes;
      state.utilityChart.update();
      return;
    }

    state.utilityChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Total volume (gal)',
            data: volumes,
            backgroundColor: '#2563eb',
          },
        ],
      },
      options: {
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
        },
      },
    });
  }

  function renderTable(records) {
    const tbody = document.getElementById('records-table-body');
    tbody.innerHTML = '';
    if (!records || records.length === 0) {
      const row = document.createElement('tr');
      const cell = document.createElement('td');
      cell.colSpan = 6;
      cell.textContent = 'No records found for the selected filters.';
      row.appendChild(cell);
      tbody.appendChild(row);
      return;
    }

    records.forEach((record) => {
      const row = document.createElement('tr');
      const cells = [
        record.date_sso_began ? record.date_sso_began.slice(0, 10) : '–',
        record.utility_name || '–',
        record.county || '–',
        formatNumber(record.volume_gallons),
        record.cause || '–',
        record.receiving_water || '–',
      ];
      cells.forEach((value) => {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.appendChild(cell);
      });
      tbody.appendChild(row);
    });
  }

  async function refreshDashboard() {
    const params = buildQueryParams();
    if (!ensureFilters(params)) {
      setStatus('Please add at least one filter (utility, county, or date range).', true);
      return;
    }
    setStatus('Loading...');
    const query = params.toString();
    try {
      const [summary, seriesDate, seriesUtility, records] = await Promise.all([
        fetchJson(`/summary?${query}`),
        fetchJson(`/series/by_date?${query}`),
        fetchJson(`/series/by_utility?${query}`),
        fetchJson(`/records?${query}`),
      ]);
      renderSummary(summary);
      renderTimeSeries(seriesDate.points || []);
      renderUtilityBars(seriesUtility.bars || []);
      renderTable(records.records || []);
      setStatus('');
    } catch (err) {
      setStatus('Failed to load dashboard data. Please adjust filters and try again.', true);
    }
  }

  function wireEvents() {
    document.getElementById('apply-filters').addEventListener('click', refreshDashboard);
    document.getElementById('download-csv').addEventListener('click', () => {
      const params = buildQueryParams();
      if (!ensureFilters(params)) {
        setStatus('Please add at least one filter to download.', true);
        return;
      }
      window.location.href = `/download?${params.toString()}`;
    });
  }

  document.addEventListener('DOMContentLoaded', async () => {
    setDefaultDates();
    await loadFilters();
    wireEvents();
  });
})();
