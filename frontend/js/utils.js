/* ==========================================================================
   VoxAgent AI — Shared Utilities
   Formatting helpers, badge/icon mappings, toast notifications, debounce.
   Loaded on every page, before any page-specific script.
   ========================================================================== */
(function (global) {
  'use strict';

  const LANGUAGE_NAMES = {
    en: 'English', es: 'Spanish', fr: 'French', de: 'German',
    hi: 'Hindi', pt: 'Portuguese', ja: 'Japanese', zh: 'Chinese',
    ar: 'Arabic', ru: 'Russian', it: 'Italian', ko: 'Korean',
  };

  const SENTIMENT_META = {
    positive: { label: 'Positive', className: 'sentiment-positive', icon: 'fa-face-smile' },
    neutral: { label: 'Neutral', className: 'sentiment-neutral', icon: 'fa-face-meh' },
    negative: { label: 'Negative', className: 'sentiment-negative', icon: 'fa-face-frown' },
  };

  function formatDuration(totalSeconds) {
    const s = Math.max(0, Math.floor(totalSeconds || 0));
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${String(m).padStart(2, '0')}:${String(rem).padStart(2, '0')}`;
  }

  function formatDate(isoString, opts = {}) {
    if (!isoString) return '—';
    const date = new Date(isoString);
    return date.toLocaleDateString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric', ...opts,
    });
  }

  function formatTime(isoString) {
    if (!isoString) return '—';
    return new Date(isoString).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  }

  function formatRelative(isoString) {
    if (!isoString) return '—';
    const diffMs = Date.now() - new Date(isoString).getTime();
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }

  function languageName(code) {
    return LANGUAGE_NAMES[code] || (code ? code.toUpperCase() : 'Unknown');
  }

  function sentimentMeta(sentiment) {
    return SENTIMENT_META[sentiment] || SENTIMENT_META.neutral;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str ?? '';
    return div.innerHTML;
  }

  function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
  }

  function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
  }

  function formatBytes(bytes) {
    if (!bytes) return '0 KB';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  }

  /* ---------------------------------------------------------------------
     Toast notifications — expects a #toastContainer element on the page
     (falls back to creating one).
     --------------------------------------------------------------------- */
  function toast(message, type = 'info', duration = 3500) {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:200;display:flex;flex-direction:column;gap:8px;';
      document.body.appendChild(container);
    }

    const icons = { success: 'fa-circle-check', error: 'fa-circle-exclamation', info: 'fa-circle-info' };
    const colors = { success: 'var(--accent-green)', error: 'var(--accent-red)', info: 'var(--accent-primary)' };

    const el = document.createElement('div');
    el.className = 'toast glass-panel';
    el.style.cssText = `display:flex;align-items:center;gap:10px;padding:12px 16px;border-left:3px solid ${colors[type] || colors.info};min-width:240px;`;
    el.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}" style="color:${colors[type] || colors.info}"></i><span style="font-size:var(--fs-sm)">${escapeHtml(message)}</span>`;

    container.appendChild(el);
    setTimeout(() => {
      el.style.transition = 'opacity 200ms ease';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 200);
    }, duration);
  }

  global.VoxUtils = {
    formatDuration, formatDate, formatTime, formatRelative,
    languageName, sentimentMeta, escapeHtml, capitalize,
    debounce, formatBytes, toast,
  };
})(window);