/* ==========================================================================
   VoxAgent AI — Chart.js Builders
   Shared chart factories used by dashboard.html and analytics.html so every
   chart shares the same color palette, fonts, and tooltip styling.
   Requires Chart.js (loaded via CDN in each page) + utils.js.
   ========================================================================== */
(function (global) {
  'use strict';

  function themeColors() {
    const styles = getComputedStyle(document.body);
    return {
      primary: styles.getPropertyValue('--accent-primary').trim() || '#7c5cff',
      blue: styles.getPropertyValue('--accent-blue').trim() || '#3b82f6',
      green: styles.getPropertyValue('--accent-green').trim() || '#22c55e',
      red: styles.getPropertyValue('--accent-red').trim() || '#ef4444',
      orange: styles.getPropertyValue('--accent-orange').trim() || '#f59e0b',
      text: styles.getPropertyValue('--text-muted').trim() || '#8892a6',
      grid: styles.getPropertyValue('--border-glass').trim() || 'rgba(255,255,255,0.08)',
    };
  }

  const baseFont = { family: getComputedStyle(document.body).getPropertyValue('--font-body') || 'Inter', size: 12 };

  function lineChart(canvasId, { labels, datasets }) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const c = themeColors();

    return new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: datasets.map((ds, i) => ({
          label: ds.label,
          data: ds.data,
          borderColor: ds.color || [c.primary, c.blue, c.green][i % 3],
          backgroundColor: (ds.color || [c.primary, c.blue, c.green][i % 3]) + '22',
          fill: ds.fill ?? true,
          tension: 0.4,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: datasets.length > 1, labels: { color: c.text, font: baseFont, usePointStyle: true } },
          tooltip: { backgroundColor: '#1a1f2e', titleColor: '#fff', bodyColor: '#fff', borderColor: c.grid, borderWidth: 1, padding: 10 },
        },
        scales: {
          x: { grid: { color: c.grid, drawBorder: false }, ticks: { color: c.text, font: baseFont } },
          y: { grid: { color: c.grid, drawBorder: false }, ticks: { color: c.text, font: baseFont }, beginAtZero: true },
        },
      },
    });
  }

  function barChart(canvasId, { labels, data, colors }) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const c = themeColors();

    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: colors || labels.map(() => c.primary),
          borderRadius: 6,
          maxBarThickness: 36,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { backgroundColor: '#1a1f2e', padding: 10 } },
        scales: {
          x: { grid: { display: false }, ticks: { color: c.text, font: baseFont } },
          y: { grid: { color: c.grid, drawBorder: false }, ticks: { color: c.text, font: baseFont }, beginAtZero: true },
        },
      },
    });
  }

  function donutChart(canvasId, { labels, data }) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const c = themeColors();
    const palette = [c.primary, c.blue, c.green, c.orange, c.red, '#a78bfa', '#f472b6'];

    return new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{ data, backgroundColor: labels.map((_, i) => palette[i % palette.length]), borderWidth: 0, hoverOffset: 6 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
          legend: { position: 'right', labels: { color: c.text, font: baseFont, usePointStyle: true, padding: 14 } },
          tooltip: { backgroundColor: '#1a1f2e', padding: 10 },
        },
      },
    });
  }

  function sentimentStackedChart(canvasId, { labels, positive, neutral, negative }) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const c = themeColors();

    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'Positive', data: positive, backgroundColor: c.green, stack: 's' },
          { label: 'Neutral', data: neutral, backgroundColor: c.text, stack: 's' },
          { label: 'Negative', data: negative, backgroundColor: c.red, stack: 's' },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: c.text, font: baseFont, usePointStyle: true } }, tooltip: { backgroundColor: '#1a1f2e', padding: 10 } },
        scales: {
          x: { stacked: true, grid: { display: false }, ticks: { color: c.text, font: baseFont } },
          y: { stacked: true, grid: { color: c.grid, drawBorder: false }, ticks: { color: c.text, font: baseFont } },
        },
      },
    });
  }

  global.VoxCharts = { lineChart, barChart, donutChart, sentimentStackedChart, themeColors };
})(window);