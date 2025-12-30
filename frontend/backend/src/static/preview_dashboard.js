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
    if (Math.abs(num) >= 1_000) {
      return `${(num / 1_000).toFixed(1)}k`;
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

  function parseDate(value) {
    if (!value) return null;
    const parsed = new Date(`${value}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function buildRangeInfo(range) {
    if (!range) return null;
    const start = parseDate(range.min);
    const end = parseDate(range.max);
    if (!start || !end) return null;
    const diffMs = end.getTime() - start.getTime();
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24)) + 1;
    return { start, end, days, label: formatDateRange(range) };
  }

  function describeDuration(hours) {
    if (!hours || hours <= 0) return 'Raw sewage was spilling for less than an hour over this period.';
    const wholeHours = Math.floor(hours);
    let daysTotal;
    let remainingHours;
    [daysTotal, remainingHours] = divmod(wholeHours, 24);
    let years;
    [years, daysTotal] = divmod(daysTotal, 365);
    let weeks;
    [weeks, daysTotal] = divmod(daysTotal, 7);
    const days = daysTotal;

    const parts = [];
    if (years) parts.push(`${years} year${years === 1 ? '' : 's'}`);
    if (weeks) parts.push(`${weeks} week${weeks === 1 ? '' : 's'}`);
    if (days) parts.push(`${days} day${days === 1 ? '' : 's'}`);
    if (remainingHours) parts.push(`${remainingHours} hour${remainingHours === 1 ? '' : 's'}`);
    if (!parts.length) parts.push(`${wholeHours} hour${wholeHours === 1 ? '' : 's'}`);

    const description = parts.join(', ');
    return `Raw sewage was spilling for about ${description} over this period.`;
  }

  function divmod(value, divisor) {
    const quotient = Math.floor(value / divisor);
    const remainder = value % divisor;
    return [quotient, remainder];
  }

  function buildQueryParams() {
    const params = new URLSearchParams();
    const utilityValue = document.getElementById('utility-search').value.trim();
    const permitValue = document.getElementById('permit-search').value.trim();
    const countyValue = document.getElementById('county-search').value.trim();
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;

    if (utilityValue) params.set('utility_name', utilityValue);
    if (permitValue) params.set('permit', permitValue);
    if (countyValue) params.set('county', countyValue);
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    return params;
  }

  function ensureFilters(params) {
    return (
      params.has('utility_name') ||
      params.has('permit') ||
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
      const permits = (item.permits || []).join(', ');
      option.value = item.name;
      option.label = permits ? `${item.name} (${permits})` : item.name;
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
      state.utilities = (data.permittees || data.utilities || []).sort((a, b) => a.name.localeCompare(b.name));
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
    if (!hasData) {
      Object.keys(state).forEach((key) => {
        const maybeChart = state[key];
        if (maybeChart && typeof maybeChart.destroy === 'function') {
          maybeChart.destroy();
          state[key] = null;
        }
      });
    }
  }

  function destroyChart(chart) {
    if (chart) chart.destroy();
  }

  function renderCards(summary, rangeInfo) {
    const counts = summary.summary_counts || {};
    const totalSpills = counts.total_spills ?? counts.total_records ?? 0;
    const totalVolume = counts.total_volume_gallons || 0;
    const durationHours = counts.total_duration_hours || 0;
    const distinctUtilities = counts.distinct_utilities;
    const distinctWaters = counts.distinct_receiving_waters;

    const days = rangeInfo?.days || 0;
    const hours = days ? days * 24 : 0;
    const spillsPerDay = days ? (totalSpills / days).toFixed(1) : '–';
    const gallonsPerHour = hours ? (totalVolume / hours).toFixed(1) : '–';
    const startLabel = rangeInfo?.start
      ? rangeInfo.start.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
      : 'the selected period';
    const endLabel = rangeInfo?.end
      ? rangeInfo.end.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
      : 'the selected period';

    const spillsText = `There were ${formatNumber(totalSpills, { allowMillions: false })} raw sewage spills from ${startLabel} to ${endLabel}. That’s about ${spillsPerDay} spills per day.`;
    const volumeText = `From ${startLabel} to ${endLabel}, ${formatNumber(totalVolume)} gallons of raw sewage were reported. That’s about ${gallonsPerHour} gallons spilled per hour.`;

    document.getElementById('card-spills-text').textContent = spillsText;
    document.getElementById('card-volume-text').textContent = volumeText;
    document.getElementById('card-duration-text').textContent = describeDuration(durationHours);
    document.getElementById('card-date-range').textContent = rangeInfo?.label || '\u00a0';
    document.getElementById('card-distincts').textContent = `${formatNumber(distinctUtilities, { allowMillions: false })} utilities, ${formatNumber(distinctWaters, { allowMillions: false })} receiving waters`;
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

    const comparisons = [];
    if (pools >= 0.5) comparisons.push(`${Math.round(pools)} Olympic swimming pools`);
    if (kegs >= 1) comparisons.push(`${Math.round(kegs).toLocaleString()} kegs of beer`);
    if (balloons >= 10) comparisons.push(`${Math.round(balloons).toLocaleString()} water balloons`);
    if (depthInches >= 0.1) comparisons.push(`enough to cover a football field about ${depthInches.toFixed(1)} inches deep`);

    const lead = `Approximately ${formatNumber(volume)} gallons of raw sewage were reported over this period.`;
    if (!comparisons.length) {
      textEl.textContent = lead;
      card.classList.remove('hidden');
      return;
    }

    const finalText = `${lead} That’s roughly the same as ${comparisons
      .map((text, idx) => {
        if (idx === comparisons.length - 1 && comparisons.length > 1) {
          return `or ${text}`;
        }
        return text;
      })
      .join(comparisons.length > 2 ? ', ' : ' ')}.`;

    textEl.textContent = finalText;
    card.classList.remove('hidden');
  }

  function renderTimeSeries(summary, rangeInfo) {
    const { time_series: timeSeries } = summary;
    const countCanvas = document.getElementById('chart-count');
    const volumeCanvas = document.getElementById('chart-volume');
    const countEmpty = document.getElementById('chart-count-empty');
    const volumeEmpty = document.getElementById('chart-volume-empty');
    const wrapper = document.getElementById('charts-time-series');
    const note = document.getElementById('chart-range-note');

    const days = rangeInfo?.days || 0;
    const points = (timeSeries && timeSeries.points) || [];
    if (days < 60) {
      wrapper.classList.add('hidden');
      note.classList.remove('hidden');
      note.textContent = 'Time-series charts are shown for date windows of 60 days or longer.';
      countEmpty.hidden = true;
      volumeEmpty.hidden = true;
      countCanvas.hidden = true;
      volumeCanvas.hidden = true;
      destroyChart(state.countChart);
      destroyChart(state.volumeChart);
      state.countChart = null;
      state.volumeChart = null;
      return;
    }

    if (!points.length || timeSeries.granularity === 'none') {
      wrapper.classList.remove('hidden');
      note.classList.add('hidden');
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

    note.classList.add('hidden');
    wrapper.classList.remove('hidden');
    countEmpty.hidden = true;
    volumeEmpty.hidden = true;

    const labels = points.map((point) => point.period_label);
    const counts = points.map((point) => point.spill_count || 0);
    const volumes = points.map((point) => point.total_volume_gallons || 0);

    countCanvas.hidden = false;
    volumeCanvas.hidden = false;

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
    if (state[chartKey]) {
      state[chartKey].destroy();
      state[chartKey] = null;
    }

    const rowsWithVolume = (rows || []).filter((row) => {
      const volume = row.total_volume_gallons ?? row.total_volume ?? 0;
      return volume > 0;
    });

    if (!rowsWithVolume.length) {
      empty.hidden = false;
      canvas.hidden = true;
      return;
    }

    empty.hidden = true;
    canvas.hidden = false;
    const labels = rowsWithVolume.map((row) => row[labelKey]);
    const values = rowsWithVolume.map((row) => row.total_volume_gallons ?? row.total_volume ?? 0);
    const totalVolume = values.reduce((sum, value) => sum + Number(value || 0), 0);
    const colors = labels.map((_, idx) => `hsl(${(idx * 45) % 360} 70% 55%)`);

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
                const label = context.label || labels[context.dataIndex];
                const rawValue = context.raw ?? values[context.dataIndex] ?? 0;
                const percent = totalVolume ? ((rawValue / totalVolume) * 100).toFixed(1) : '0.0';
                return `${label}: ${formatNumber(rawValue)} gal (${percent}%)`;
              },
            },
          },
        },
      },
    });
  }

  function renderTopTables(summary) {
    const receiving = (summary.top_receiving_waters || [])
      .slice(0, 10)
      .map((row) => ({
        receiving_water: row.receiving_water || row.receiving_water_name || 'Unknown',
        total_volume_gallons: row.total_volume_gallons ?? row.total_volume ?? 0,
        spill_count: row.spill_count || 0,
      }));
    const utilities = summary.top_utilities || [];
    renderTable('receiving-table', receiving, ['receiving_water', 'total_volume_gallons', 'spill_count']);
    renderTable('utility-table', utilities, ['utility_name', 'spill_count', 'total_volume_gallons']);
    attachSorting('receiving-table', receiving, ['receiving_water', 'total_volume_gallons', 'spill_count']);
    attachSorting('utility-table', utilities, ['utility_name', 'spill_count', 'total_volume_gallons']);
  }

  function renderPies(summary, isSpecificUtility) {
    const receivingPie = summary.receiving_waters_pie || [];
    const utilityPie = isSpecificUtility ? [] : summary.top_utilities_pie || [];
    renderPie('receiving-pie', 'pie-empty', receivingPie, 'receiving_water');
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
      const rangeInfo = buildRangeInfo(counts.date_range);
      const hasData = (response.top_receiving_waters && response.top_receiving_waters.length) || counts.total_records;
      toggleVisibility(Boolean(hasData));
      if (!hasData) {
        setStatus('No data found for the selected filters.', false);
        return;
      }

      renderCards(response, rangeInfo);
      renderEquivalents(response);
      renderTimeSeries(response, rangeInfo);
      renderTopTables(response);
      const hasUtilityFilter = params.has('utility_name') || params.has('permit');
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
