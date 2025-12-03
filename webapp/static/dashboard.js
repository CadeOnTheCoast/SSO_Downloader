(function () {
  const state = {
    timeSeriesChart: null,
    utilityChart: null,
    bucketChart: null,
    volumeShareChart: null,
    receivingChart: null,
    lastFilters: null,
  };

  const MAX_UTILITY_BARS = 10;

  function setStatus(message, isError = false) {
    const el = document.getElementById('status');
    if (!el) return;
    el.textContent = message || '';
    el.style.color = isError ? '#b91c1c' : '#0f172a';
  }

  function formatNumber(value, maximumFractionDigits = 1) {
    if (value === null || value === undefined) return '–';
    if (isNaN(value)) return String(value);
    return Number(value).toLocaleString(undefined, {
      maximumFractionDigits,
    });
  }

  function formatCompactNumber(value) {
    if (value === null || value === undefined || isNaN(value)) return '–';
    const abs = Math.abs(value);
    if (abs >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
    if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (abs >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
    return formatNumber(value, 0);
  }

  function formatDurationFromHours(hours) {
    if (!hours || hours <= 0) return '0 hours';
    const units = [
      ['year', 24 * 365],
      ['week', 24 * 7],
      ['day', 24],
      ['hour', 1],
    ];
    let remaining = Math.floor(hours);
    const parts = [];
    for (const [label, unitHours] of units) {
      const count = Math.floor(remaining / unitHours);
      if (count > 0) {
        parts.push(`${count} ${label}${count !== 1 ? 's' : ''}`);
        remaining -= count * unitHours;
      }
      if (parts.length === 2) break;
    }
    return parts.join(', ');
  }

  function formatDateRange(range) {
    if (!range) return '';
    const { min, max } = range;
    if (min && max) return `${min} – ${max}`;
    if (min) return `Since ${min}`;
    if (max) return `Through ${max}`;
    return '';
  }

  function calcDateRangeDays(range) {
    if (!range || !range.min || !range.max) return { days: 0, hours: 0 };
    const start = new Date(range.min);
    const end = new Date(range.max);
    if (Number.isNaN(start) || Number.isNaN(end)) return { days: 0, hours: 0 };
    const msPerDay = 1000 * 60 * 60 * 24;
    const days = Math.floor((end - start) / msPerDay) + 1;
    return { days: days > 0 ? days : 0, hours: Math.max(days, 0) * 24 };
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

      attachSearchFilter('utility-search', utilitySelect);
      attachSearchFilter('county-search', countySelect);
    } catch (err) {
      setStatus('Unable to load filter options.', true);
    }
  }

  function attachSearchFilter(inputId, selectEl) {
    const input = document.getElementById(inputId);
    if (!input || !selectEl) return;
    input.addEventListener('input', () => {
      const query = input.value.toLowerCase();
      Array.from(selectEl.options).forEach((opt, index) => {
        if (index === 0) return;
        const text = opt.textContent.toLowerCase();
        opt.hidden = query ? !text.includes(query) : false;
      });
    });
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
    const range = counts.date_range || {};
    const rangeLabel = formatDateRange(range) || ' ';
    const { days, hours } = calcDateRangeDays(range);
    const totalRecords = counts.total_records || 0;
    const totalVolume = counts.total_volume ?? counts.total_volume_gallons ?? 0;
    const totalDuration = counts.total_duration_hours || 0;

    const spillsPerDay = days > 0 ? totalRecords / days : totalRecords;
    document.getElementById('card-total-spills').textContent = formatNumber(totalRecords, 0);
    document.getElementById('card-total-spills-text').textContent =
      `There were ${formatNumber(totalRecords, 0)} raw sewage spills from ${rangeLabel}. That’s about ${formatNumber(
        spillsPerDay,
        1
      )} spills per day.`;

    document.getElementById('card-total-volume').textContent = formatCompactNumber(totalVolume);
    const gallonsPerHour = hours > 0 ? totalVolume / hours : totalVolume;
    document.getElementById('card-total-volume-text').textContent =
      `About ${formatNumber(totalVolume, 0)} gallons of raw sewage spilled in this period – roughly ${formatNumber(
        gallonsPerHour,
        0
      )} gallons every hour.`;

    const durationLabel = formatDurationFromHours(totalDuration);
    document.getElementById('card-total-duration').textContent = durationLabel;
    document.getElementById('card-total-duration-text').textContent =
      `Raw sewage was spilling for a combined ${durationLabel} during this period.`;

    const olympicPools = totalVolume / 660_000;
    const tankerTrucks = totalVolume / 7_000;
    const equivalence = `${formatNumber(olympicPools, 1)} Olympic pools`;
    document.getElementById('card-equivalence').textContent = equivalence;
    document.getElementById('card-equivalence-text').textContent =
      `That’s enough raw sewage to fill ${formatNumber(
        olympicPools,
        1
      )} Olympic swimming pools or ${formatNumber(tankerTrucks, 0)} tanker trucks.`;
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

  function renderVolumeShare(topUtilities) {
    const emptyEl = document.getElementById('volume-share-empty');
    const canvas = document.getElementById('volume-share-chart');
    const top = topUtilities || [];
    const labels = top.map((u) => u.utility_name || u.utility_id || 'Unknown');
    const data = top.map((u) => u.total_volume_gallons || u.total_volume || 0);

    if (!labels.length || !data.some((val) => val > 0)) {
      emptyEl.hidden = false;
      canvas.hidden = true;
      destroyChart('volumeShareChart');
      return;
    }

    emptyEl.hidden = true;
    canvas.hidden = false;

    destroyChart('volumeShareChart');
    state.volumeShareChart = new Chart(canvas, {
      type: 'pie',
      data: {
        labels,
        datasets: [
          {
            data,
            backgroundColor: labels.map((_, idx) => `hsl(${(idx * 55) % 360}, 65%, 60%)`),
          },
        ],
      },
      options: {
        plugins: {
          tooltip: {
            callbacks: {
              label: (context) => {
                const value = context.parsed || 0;
                const dataset = context.dataset.data || [];
                const total = dataset.reduce((sum, val) => sum + (val || 0), 0) || 0;
                const percent = total ? ((value / total) * 100).toFixed(1) : '0.0';
                return `${context.label}: ${formatNumber(value, 0)} gal (${percent}%)`;
              },
            },
          },
          legend: { position: 'bottom' },
        },
      },
    });
  }

  function renderReceivingWaterChart(rows) {
    const emptyEl = document.getElementById('receiving-empty');
    const canvas = document.getElementById('receiving-chart');

    if (!rows || !rows.length) {
      emptyEl.hidden = false;
      canvas.hidden = true;
      destroyChart('receivingChart');
      return;
    }

    emptyEl.hidden = true;
    canvas.hidden = false;

    const labels = rows.map((row) => row.name || 'Unknown');
    const data = rows.map((row) => row.total_volume || 0);

    destroyChart('receivingChart');
    state.receivingChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Total volume (gal)',
            data,
            backgroundColor: '#8b5cf6',
          },
        ],
      },
      options: {
        indexAxis: 'y',
        plugins: { legend: { display: false } },
      },
    });
  }

  function renderReceivingWaterTable(rows) {
    const tbody = document.getElementById('receiving-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    const list = rows || [];
    if (!list.length) {
      const row = document.createElement('tr');
      const cell = document.createElement('td');
      cell.colSpan = 3;
      cell.textContent = 'No receiving water data for this selection.';
      row.appendChild(cell);
      tbody.appendChild(row);
      return;
    }

    list.forEach((row) => {
      const tr = document.createElement('tr');
      const cells = [
        row.name || 'Unknown',
        formatNumber(row.total_volume || 0, 0),
        formatNumber(row.spills || 0, 0),
      ];
      cells.forEach((value) => {
        const td = document.createElement('td');
        td.textContent = value;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
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
      renderVolumeShare(summary.top_utilities_pie || summary.top_utilities || []);
      renderReceivingWaterChart(summary.by_receiving_water || []);
      renderReceivingWaterTable(summary.by_receiving_water || []);
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
