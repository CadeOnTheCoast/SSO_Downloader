(function () {
  const state = {
    timeSeriesChart: null,
    utilityChart: null,
    bucketChart: null,
    lastFilters: null,
  };

  const MAX_UTILITY_BARS = 10;

  function setStatus(message, isError = false) {
    const el = document.getElementById('status');
    if (!el) return;
    el.textContent = message || '';
    el.style.color = isError ? '#b91c1c' : '#0f172a';
  }

  function formatNumber(value) {
    if (value === null || value === undefined) return '–';
    if (isNaN(value)) return String(value);
    return Number(value).toLocaleString(undefined, {
      maximumFractionDigits: 1,
    });
  }

  function formatDateRange(range) {
    if (!range) return '';
    const { min, max } = range;
    if (min && max) return `${min} – ${max}`;
    if (min) return `Since ${min}`;
    if (max) return `Through ${max}`;
    return '';
  }

  function formatMonthLabel(monthKey) {
    if (!monthKey) return '';
    const [year, month] = monthKey.split('-').map((part) => Number(part));
    const date = new Date(year, month - 1, 1);
    return date.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
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
      let data;
      try {
        data = await fetchJson('/api/options');
      } catch (err) {
        data = await fetchJson('/filters');
      }
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
      setStatus('Unable to load filter options.', true);
    }
  }

  function setDefaultDates() {
    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - 6);
    document.getElementById('end-date').value = end.toISOString().slice(0, 10);
    document.getElementById('start-date').value = start.toISOString().slice(0, 10);
  }

  function buildFilters() {
    return {
      utility_id: document.getElementById('utility-select').value,
      county: document.getElementById('county-select').value,
      start_date: document.getElementById('start-date').value,
      end_date: document.getElementById('end-date').value,
      limit: document.getElementById('record-limit').value,
    };
  }

  function buildQueryString(filters) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        params.set(key, value);
      }
    });
    return params.toString();
  }

  function ensureFilters(filters) {
    return (
      filters.utility_id ||
      filters.county ||
      filters.start_date ||
      filters.end_date
    );
  }

  function updateDownloadLink(filters) {
    const params = buildQueryString(filters);
    document.getElementById('download-csv').onclick = () => {
      if (!ensureFilters(filters)) {
        setStatus('Please add at least one filter to download.', true);
        return;
      }
      window.location.href = `/api/ssos.csv?${params}`;
    };
  }

  function destroyChart(chartKey) {
    if (state[chartKey]) {
      state[chartKey].destroy();
      state[chartKey] = null;
    }
  }

  function renderSummary(data) {
    const counts = data.summary_counts || {};
    document.getElementById('summary-total-count').textContent = formatNumber(
      counts.total_records
    );
    document.getElementById('summary-total-volume').textContent = formatNumber(
      counts.total_volume
    );
    document.getElementById('summary-avg-volume').textContent = formatNumber(
      counts.avg_volume
    );
    document.getElementById('summary-max-volume').textContent = formatNumber(
      counts.max_volume
    );
    document.getElementById('summary-distinct-utilities').textContent = formatNumber(
      counts.distinct_utilities
    );
    const rangeLabel = formatDateRange(counts.date_range);
    document.getElementById('summary-date-range').textContent = rangeLabel || '\u00a0';
  }

  function renderTimeSeries(rows) {
    const emptyEl = document.getElementById('time-series-empty');
    const canvas = document.getElementById('time-series-chart');
    if (!rows || rows.length === 0) {
      emptyEl.hidden = false;
      canvas.hidden = true;
      destroyChart('timeSeriesChart');
      return;
    }

    emptyEl.hidden = true;
    canvas.hidden = false;

    const labels = rows.map((row) => formatMonthLabel(row.month));
    const counts = rows.map((row) => row.spill_count || 0);
    const volumes = rows.map((row) => row.total_volume || 0);

    if (state.timeSeriesChart) {
      state.timeSeriesChart.data.labels = labels;
      state.timeSeriesChart.data.datasets[0].data = counts;
      state.timeSeriesChart.data.datasets[1].data = volumes;
      state.timeSeriesChart.update();
      return;
    }

    state.timeSeriesChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Spills',
            data: counts,
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37, 99, 235, 0.15)',
            tension: 0.2,
            yAxisID: 'y',
          },
          {
            label: 'Total volume (gal)',
            data: volumes,
            borderColor: '#0ea5e9',
            backgroundColor: 'rgba(14, 165, 233, 0.15)',
            tension: 0.2,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: { position: 'left', title: { display: true, text: 'Spills' } },
          y1: {
            position: 'right',
            grid: { drawOnChartArea: false },
            title: { display: true, text: 'Volume (gal)' },
          },
        },
        plugins: { legend: { position: 'bottom' } },
      },
    });
  }

  function renderUtilityBars(rows) {
    const emptyEl = document.getElementById('utility-empty');
    const canvas = document.getElementById('utility-chart');

    if (!rows || rows.length === 0) {
      emptyEl.hidden = false;
      canvas.hidden = true;
      destroyChart('utilityChart');
      return;
    }

    emptyEl.hidden = true;
    canvas.hidden = false;

    const sorted = [...rows].sort((a, b) => (b.total_volume || 0) - (a.total_volume || 0));
    const limited = sorted.slice(0, MAX_UTILITY_BARS);
    const labels = limited.map(
      (row) => row.utility_name || row.utility_id || row.group_key || 'Unknown'
    );
    const volumes = limited.map((row) => row.total_volume || 0);

    if (state.utilityChart) {
      state.utilityChart.data.labels = labels;
      state.utilityChart.data.datasets[0].data = volumes;
      state.utilityChart.update();
      return;
    }

    state.utilityChart = new Chart(canvas, {
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
        plugins: { legend: { display: false } },
      },
    });
  }

  function renderBucketChart(rows) {
    const emptyEl = document.getElementById('bucket-empty');
    const canvas = document.getElementById('bucket-chart');

    if (!rows || rows.length === 0) {
      emptyEl.hidden = false;
      canvas.hidden = true;
      destroyChart('bucketChart');
      return;
    }

    emptyEl.hidden = true;
    canvas.hidden = false;

    const labels = rows.map((row) => row.bucket_label || row.label || 'Unknown');
    const counts = rows.map((row) => row.spill_count || 0);

    if (state.bucketChart) {
      state.bucketChart.data.labels = labels;
      state.bucketChart.data.datasets[0].data = counts;
      state.bucketChart.update();
      return;
    }

    state.bucketChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Spills',
            data: counts,
            backgroundColor: '#0ea5e9',
          },
        ],
      },
      options: {
        plugins: { legend: { display: false } },
      },
    });
  }

  function renderTable(response) {
    const tbody = document.getElementById('records-table-body');
    const tableMeta = document.getElementById('table-meta-count');
    tbody.innerHTML = '';

    const records = response.items || response.records || [];
    const limit = response.limit || records.length;

    tableMeta.textContent = `Showing ${records.length} records (limit ${limit})`;

    if (!records.length) {
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
        record.utility_name || record.utility_id || '–',
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
    const filters = buildFilters();
    state.lastFilters = filters;
    if (!ensureFilters(filters)) {
      setStatus('Please add at least one filter (utility, county, or date range).', true);
      return;
    }

    setStatus('Loading...');
    updateDownloadLink(filters);
    const query = buildQueryString(filters);

    try {
      const [summary, records] = await Promise.all([
        fetchJson(`/api/ssos/summary?${query}`),
        fetchJson(`/api/ssos?${query}`),
      ]);
      renderSummary(summary);
      renderTimeSeries(summary.by_month || []);
      renderUtilityBars(summary.by_utility || []);
      renderBucketChart(summary.by_volume_bucket || []);
      renderTable(records);
      setStatus('');
    } catch (err) {
      setStatus('Failed to load dashboard data. Please adjust filters and try again.', true);
    }
  }

  function wireEvents() {
    document.getElementById('apply-filters').addEventListener('click', refreshDashboard);
    document.getElementById('download-csv').addEventListener('click', (event) => {
      event.preventDefault();
    });
  }

  document.addEventListener('DOMContentLoaded', async () => {
    setDefaultDates();
    await loadFilters();
    wireEvents();
    refreshDashboard();
  });
})();
