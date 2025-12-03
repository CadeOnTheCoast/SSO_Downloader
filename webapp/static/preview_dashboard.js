(function () {
  const state = {
    countChart: null,
    volumeChart: null,
    utilityPie: null,
    receivingPie: null,
    utilities: [],
    counties: [],
    selectedUtility: null,
  };

  function setStatus(message, isError = false) {
    const el = document.getElementById('status');
    if (!el) return;
    el.textContent = message || '';
    el.style.color = isError ? '#b91c1c' : '#0f172a';
  }

  function formatNumber(value, { allowMillions = true } = {}) {
    if (value === null || value === undefined) return '–';
    const num = Number(value);
    if (!Number.isFinite(num)) return String(value);
    if (allowMillions && Math.abs(num) >= 1_000_000) {
      return `${(num / 1_000_000).toFixed(1)}M`;
    }
    return num.toLocaleString(undefined, { maximumFractionDigits: 1 });
  }

  function formatDateRange(range) {
    if (!range) return '';
    const { min, max } = range;
    if (min && max) return `${min} – ${max}`;
    if (min) return `Since ${min}`;
    if (max) return `Through ${max}`;
    return '';
  }

  function buildQueryParams() {
    const params = new URLSearchParams();
    const utilityValue = document.getElementById('utility-search').value.trim();
    const countyValue = document.getElementById('county-search').value.trim();
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;

    if (utilityValue) params.set('utility_id', utilityValue);
    if (countyValue) params.set('county', countyValue);
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
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

  function populateOptions() {
    const utilityList = document.getElementById('utility-options');
    const countyList = document.getElementById('county-options');
    utilityList.innerHTML = '';
    countyList.innerHTML = '';

    const anyUtility = document.createElement('option');
    anyUtility.value = '';
    anyUtility.label = '-- any utility --';
    utilityList.appendChild(anyUtility);

    state.utilities.forEach((item) => {
      const option = document.createElement('option');
      option.value = item.id;
      option.label = `${item.name} (${item.id})`;
      utilityList.appendChild(option);
    });

    const anyCounty = document.createElement('option');
    anyCounty.value = '';
    anyCounty.label = '-- any county --';
    countyList.appendChild(anyCounty);

    state.counties.forEach((name) => {
      const option = document.createElement('option');
      option.value = name;
      option.label = name;
      countyList.appendChild(option);
    });
  }

  async function loadOptions() {
    try {
      let data;
      try {
        data = await fetchJson('/api/options');
      } catch (err) {
        data = await fetchJson('/filters');
      }
      state.utilities = (data.utilities || []).sort((a, b) => a.name.localeCompare(b.name));
      state.counties = (data.counties || []).sort((a, b) => a.localeCompare(b));
      populateOptions();
    } catch (err) {
      setStatus('Unable to load filter options.', true);
    }
  }

  function clearInput(id) {
    const el = document.getElementById(id);
    if (el) el.value = '';
  }

  function wireClearButtons() {
    document.querySelectorAll('.clear-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = btn.getAttribute('data-target');
        clearInput(target);
      });
    });
  }

  function updateDownloadLink(params) {
    const button = document.getElementById('download');
    const query = params.toString();
    button.onclick = () => {
      if (!ensureFilters(params)) {
        setStatus('Please add at least one filter before downloading.', true);
        return;
      }
      window.location.href = `/api/ssos.csv?${query}`;
    };
  }

  function setDateDefaults() {
    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - 3);
    document.getElementById('end_date').value = end.toISOString().slice(0, 10);
    document.getElementById('start_date').value = start.toISOString().slice(0, 10);
  }

  function toggleVisibility(hasData) {
    document.getElementById('dashboard').classList.toggle('hidden', !hasData);
    document.getElementById('empty-message').classList.toggle('hidden', hasData);
  }

  function destroyChart(chart) {
    if (chart) chart.destroy();
  }

  function renderCards(summary) {
    const counts = summary.summary_counts || {};
    document.getElementById('card-total-spills').textContent = formatNumber(counts.total_records, { allowMillions: false });
    document.getElementById('card-total-volume').textContent = formatNumber(counts.total_volume_gallons || 0);
    document.getElementById('card-total-duration').textContent = formatNumber(counts.total_duration_hours || 0, { allowMillions: false });
    document.getElementById('card-distinct-utils').textContent = formatNumber(counts.distinct_utilities, { allowMillions: false });
    document.getElementById('card-distinct-waters').textContent = formatNumber(counts.distinct_receiving_waters, { allowMillions: false });
    document.getElementById('card-date-range').textContent = formatDateRange(counts.date_range) || '\u00a0';
  }

  function renderEquivalents(summary) {
    const counts = summary.summary_counts || {};
    const volume = counts.total_volume_gallons || 0;
    const card = document.getElementById('equivalents-card');
    const textEl = document.getElementById('equivalents-text');

    if (!volume || volume <= 0) {
      textEl.textContent = 'Not enough data to calculate equivalents yet.';
      card.classList.add('hidden');
      return;
    }

    const pools = volume / 660_000;
    const kegs = volume / 15.5;
    const balloons = volume / 0.1;
    const depthFt = (volume / 7.48) / (360 * 160);
    const depthInches = depthFt * 12;

    const parts = [
      `Approximately ${formatNumber(volume)} gallons reported over this period.`,
    ];
    if (pools >= 0.5) parts.push(`${Math.round(pools)} Olympic swimming pools`);
    if (kegs >= 1) parts.push(`${Math.round(kegs).toLocaleString()} kegs of beer`);
    if (balloons >= 10) parts.push(`${Math.round(balloons).toLocaleString()} water balloons`);
    if (depthInches >= 0.1) parts.push(`enough to cover a football field about ${depthInches.toFixed(1)} inches deep`);

    textEl.textContent = parts.join(', ');
    card.classList.toggle('hidden', parts.length === 0);
  }

  function renderTimeSeries(summary) {
    const { time_series: timeSeries } = summary;
    const countCanvas = document.getElementById('chart-count');
    const volumeCanvas = document.getElementById('chart-volume');
    const countEmpty = document.getElementById('chart-count-empty');
    const volumeEmpty = document.getElementById('chart-volume-empty');

    const points = (timeSeries && timeSeries.points) || [];
    if (!points.length || timeSeries.granularity === 'none') {
      countEmpty.hidden = false;
      volumeEmpty.hidden = false;
      countCanvas.hidden = true;
      volumeCanvas.hidden = true;
      destroyChart(state.countChart);
      destroyChart(state.volumeChart);
      state.countChart = null;
      state.volumeChart = null;
      return;
    }

    countEmpty.hidden = true;
    volumeEmpty.hidden = true;
    countCanvas.hidden = false;
    volumeCanvas.hidden = false;

    const labels = points.map((point) => point.period_label);
    const counts = points.map((point) => point.spill_count || 0);
    const volumes = points.map((point) => point.total_volume_gallons || 0);

    if (state.countChart) {
      state.countChart.data.labels = labels;
      state.countChart.data.datasets[0].data = counts;
      state.countChart.update();
    } else {
      state.countChart = new Chart(countCanvas, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: 'Spills',
              data: counts,
              borderColor: '#2563eb',
              backgroundColor: 'rgba(37, 99, 235, 0.15)',
              tension: 0.25,
            },
          ],
        },
        options: { plugins: { legend: { display: false } } },
      });
    }

    if (state.volumeChart) {
      state.volumeChart.data.labels = labels;
      state.volumeChart.data.datasets[0].data = volumes;
      state.volumeChart.update();
    } else {
      state.volumeChart = new Chart(volumeCanvas, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: 'Total volume (gal)',
              data: volumes,
              borderColor: '#0ea5e9',
              backgroundColor: 'rgba(14, 165, 233, 0.15)',
              tension: 0.25,
            },
          ],
        },
        options: { plugins: { legend: { position: 'bottom' } } },
      });
    }
  }

  function renderTable(tableId, rows, columns) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    tbody.innerHTML = '';
    rows.forEach((row) => {
      const tr = document.createElement('tr');
      columns.forEach((col) => {
        const td = document.createElement('td');
        let value = row[col] ?? '–';
        if (col.includes('volume')) value = formatNumber(row[col]);
        td.textContent = value;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  function attachSorting(tableId, rows, columns) {
    const headers = document.querySelectorAll(`#${tableId} th[data-sort]`);
    headers.forEach((header) => {
      header.onclick = () => {
        const key = header.getAttribute('data-sort');
        const current = header.classList.contains('sort-asc') ? 'asc' : header.classList.contains('sort-desc') ? 'desc' : null;
        headers.forEach((h) => h.classList.remove('sort-asc', 'sort-desc'));
        const nextDir = current === 'asc' ? 'desc' : 'asc';
        header.classList.add(nextDir === 'asc' ? 'sort-asc' : 'sort-desc');
        const sorted = [...rows].sort((a, b) => {
          const aVal = a[key];
          const bVal = b[key];
          if (typeof aVal === 'string' || typeof bVal === 'string') {
            const aStr = (aVal || '').toString();
            const bStr = (bVal || '').toString();
            return nextDir === 'asc' ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
          }
          const aNum = Number(aVal) || 0;
          const bNum = Number(bVal) || 0;
          return nextDir === 'asc' ? aNum - bNum : bNum - aNum;
        });
        renderTable(tableId, sorted, columns);
      };
    });
  }

  function renderPie(canvasId, emptyId, rows, labelKey) {
    const canvas = document.getElementById(canvasId);
    const empty = document.getElementById(emptyId);
    const chartKey = `${canvasId}Chart`;
    if (!rows || !rows.length) {
      empty.hidden = false;
      canvas.hidden = true;
      if (state[chartKey]) {
        state[chartKey].destroy();
        state[chartKey] = null;
      }
      return;
    }
    empty.hidden = true;
    canvas.hidden = false;
    const labels = rows.map((row) => row[labelKey]);
    const values = rows.map((row) => row.total_volume_gallons || 0);
    const percents = rows.map((row) => (row.percent_of_total || 0).toFixed(1));
    const colors = labels.map((_, idx) => `hsl(${(idx * 45) % 360} 70% 55%)`);

    if (state[chartKey]) {
      state[chartKey].data.labels = labels;
      state[chartKey].data.datasets[0].data = values;
      state[chartKey].update();
      return;
    }

    state[chartKey] = new Chart(canvas, {
      type: 'pie',
      data: {
        labels,
        datasets: [
          {
            data: values,
            backgroundColor: colors,
          },
        ],
      },
      options: {
        plugins: {
          tooltip: {
            callbacks: {
              label(context) {
                const label = labels[context.dataIndex];
                const volume = formatNumber(values[context.dataIndex]);
                const percent = percents[context.dataIndex];
                return `${label}: ${volume} gal (${percent}%)`;
              },
            },
          },
        },
      },
    });
  }

  function renderTopTables(summary) {
    const receiving = (summary.top_receiving_waters || []).slice(0, 10);
    const utilities = summary.top_utilities || [];
    renderTable('receiving-table', receiving, ['receiving_water_name', 'total_volume_gallons', 'spill_count']);
    renderTable('utility-table', utilities, ['utility_name', 'spill_count', 'total_volume_gallons']);
    attachSorting('receiving-table', receiving, ['receiving_water_name', 'total_volume_gallons', 'spill_count']);
    attachSorting('utility-table', utilities, ['utility_name', 'spill_count', 'total_volume_gallons']);
  }

  function renderPies(summary, isSpecificUtility) {
    const receivingPie = summary.receiving_waters_pie || [];
    const utilityPie = isSpecificUtility ? [] : summary.top_utilities_pie || [];
    renderPie('receiving-pie', 'pie-empty', receivingPie, 'receiving_water_name');
    renderPie('utility-pie', 'utility-pie-empty', utilityPie, 'utility_name');
  }

  async function previewSummary() {
    const params = buildQueryParams();
    if (!ensureFilters(params)) {
      setStatus('Please add at least one filter (utility, county, or date range).', true);
      toggleVisibility(false);
      return;
    }
    setStatus('Loading...');
    updateDownloadLink(params);
    const query = params.toString();

    try {
      const response = await fetchJson(`/api/ssos/summary?${query}`);
      const counts = response.summary_counts || {};
      const hasData = (response.top_receiving_waters && response.top_receiving_waters.length) || counts.total_records;
      toggleVisibility(Boolean(hasData));
      if (!hasData) {
        setStatus('No data found for the selected filters.', false);
        return;
      }

      renderCards(response);
      renderEquivalents(response);
      renderTimeSeries(response);
      renderTopTables(response);
      const hasUtilityFilter = params.has('utility_id');
      document.getElementById('pie-title').textContent = hasUtilityFilter
        ? 'Volume by receiving water'
        : 'Volume by receiving water (all utilities)';
      renderPies(response, hasUtilityFilter);
      setStatus('');
    } catch (err) {
      setStatus('Failed to load summary. Please adjust filters and try again.', true);
      toggleVisibility(false);
    }
  }

  function wireEvents() {
    document.getElementById('preview').addEventListener('click', previewSummary);
    document.getElementById('download').addEventListener('click', (event) => {
      event.preventDefault();
      const params = buildQueryParams();
      updateDownloadLink(params);
      if (!ensureFilters(params)) {
        setStatus('Please add at least one filter (utility, county, or date range).', true);
      } else {
        window.location.href = `/api/ssos.csv?${params.toString()}`;
      }
    });
  }

  document.addEventListener('DOMContentLoaded', async () => {
    setDateDefaults();
    wireClearButtons();
    wireEvents();
    await loadOptions();
    previewSummary();
  });
})();
