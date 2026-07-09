/* ==========================================================================
   VoxAgent AI — Call Logs
   Talks to the real backend: GET /api/calls (list + filters), GET /api/calls/:id
   (transcript detail for the modal). Search/language/status are applied
   server-side; sentiment is applied client-side since the API doesn't expose
   a sentiment filter yet.
   ========================================================================== */

(function () {
  'use strict';

  if (document.body.getAttribute('data-page') !== 'call-logs') return;
  if (!window.VoxAPI.isAuthenticated()) { window.location.href = 'login.html'; return; }

  const { toast, formatDate, languageName, debounce, escapeHtml } = window.VoxUtils;

  const PAGE_SIZE = 10;
  const FETCH_SIZE = 100; // max page_size the backend accepts per request

  let allCalls = [];       // everything returned by the server for the current server-side filters
  let filteredCalls = [];  // allCalls further narrowed by the client-side sentiment filter
  let currentPage = 1;
  let loading = false;

  const el = {
    tbody: document.getElementById('callLogsBody'),
    badge: document.getElementById('callCountBadge'),
    empty: document.getElementById('callLogsEmpty'),

    prev: document.getElementById('paginationPrev'),
    next: document.getElementById('paginationNext'),
    pages: document.getElementById('paginationPages'),

    search: document.getElementById('callSearchInput'),
    language: document.getElementById('filterLanguage'),
    sentiment: document.getElementById('filterSentiment'),
    status: document.getElementById('filterStatus'),
    reset: document.getElementById('filterResetBtn'),

    modal: document.getElementById('transcriptModal'),
    modalCallId: document.getElementById('transcriptModalCallId'),
    modalMeta: document.getElementById('transcriptModalMeta'),
    modalBody: document.getElementById('transcriptModalBody'),
    modalClose: document.getElementById('transcriptModalClose'),
    modalCancel: document.getElementById('transcriptModalCancel'),
    modalFullView: document.getElementById('transcriptModalFullView'),
  };

  if (!el.tbody || !el.badge || !el.empty || !el.prev || !el.next || !el.pages) {
    console.error('Call Logs page is missing required markup.');
    return;
  }

  document.addEventListener('DOMContentLoaded', init);
  // In case this script runs after DOMContentLoaded already fired.
  if (document.readyState !== 'loading') init();

  let initialized = false;
  async function init() {
    if (initialized) return;
    initialized = true;

    bindFilters();
    bindPagination();
    bindModal();
    await loadCalls();
  }

  /* --------------------------------------------------------------------
     Data loading
     -------------------------------------------------------------------- */
  async function loadCalls() {
    if (loading) return;
    loading = true;
    showLoading();

    try {
      const params = { page: 1, page_size: FETCH_SIZE };
      const status = el.status.value;
      const language = el.language.value;
      const search = el.search.value.trim();
      if (status) params.status = status;
      if (language) params.language = language;
      if (search) params.search = search;

      const res = await window.VoxAPI.listCalls(params);
      allCalls = Array.isArray(res) ? res : (res.items || []);
      applySentimentFilter();
      currentPage = 1;
      renderTable();
    } catch (err) {
      console.error(err);
      toast(err.message, 'error');
      allCalls = [];
      filteredCalls = [];
      renderTable();
    } finally {
      loading = false;
    }
  }

  function applySentimentFilter() {
    const sentiment = el.sentiment.value;
    filteredCalls = sentiment
      ? allCalls.filter((c) => c.sentiment === sentiment)
      : allCalls.slice();
  }

  /* --------------------------------------------------------------------
     Filters
     -------------------------------------------------------------------- */
  function bindFilters() {
    const debouncedSearch = debounce(() => { currentPage = 1; loadCalls(); }, 350);

    el.search.addEventListener('input', debouncedSearch);
    el.language.addEventListener('change', () => { currentPage = 1; loadCalls(); });
    el.status.addEventListener('change', () => { currentPage = 1; loadCalls(); });
    el.sentiment.addEventListener('change', () => {
      currentPage = 1;
      applySentimentFilter();
      renderTable();
    });

    el.reset.addEventListener('click', () => {
      el.search.value = '';
      el.language.value = '';
      el.status.value = '';
      el.sentiment.value = '';
      currentPage = 1;
      loadCalls();
    });
  }

  /* --------------------------------------------------------------------
     Table rendering
     -------------------------------------------------------------------- */
  function renderTable() {
    el.tbody.innerHTML = '';

    if (!filteredCalls.length) {
      el.empty.hidden = false;
      el.badge.textContent = '0 calls found';
      renderPagination();
      return;
    }

    el.empty.hidden = true;
    el.badge.textContent = `${filteredCalls.length} call${filteredCalls.length === 1 ? '' : 's'} found`;

    const start = (currentPage - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    filteredCalls.slice(start, end).forEach(addRow);

    renderPagination();
  }

  function addRow(call) {
    const tr = document.createElement('tr');
    tr.dataset.callId = call.id;

    tr.innerHTML = `
      <td class="cell-mono">#${escapeHtml(call.call_ref || call.id)}</td>
      <td>${languagePill(call.language)}</td>
      <td>${formatDuration(call.duration_seconds)}</td>
      <td>${sentimentBadge(call.sentiment)}</td>
      <td>${statusBadge(call.status)}</td>
      <td>${formatDate(call.started_at, { hour: '2-digit', minute: '2-digit' })}</td>
      <td>
        <button class="table-icon-btn view-transcript-btn" data-id="${escapeHtml(call.id)}" title="View transcript">
          <i class="fa-solid fa-eye"></i>
        </button>
      </td>
    `;

    el.tbody.appendChild(tr);
  }

  function bindPagination() {
    el.prev.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        renderTable();
      }
    });

    el.next.addEventListener('click', () => {
      const maxPage = Math.max(1, Math.ceil(filteredCalls.length / PAGE_SIZE));
      if (currentPage < maxPage) {
        currentPage++;
        renderTable();
      }
    });
  }

  function renderPagination() {
    const maxPage = Math.max(1, Math.ceil(filteredCalls.length / PAGE_SIZE));
    el.prev.disabled = currentPage <= 1;
    el.next.disabled = currentPage >= maxPage;

    el.pages.innerHTML = '';
    for (let p = 1; p <= maxPage; p++) {
      const btn = document.createElement('button');
      btn.className = 'pagination-page' + (p === currentPage ? ' active' : '');
      btn.textContent = String(p);
      btn.addEventListener('click', () => {
        currentPage = p;
        renderTable();
      });
      el.pages.appendChild(btn);
    }
  }

  function showLoading() {
    el.empty.hidden = true;
    el.tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center; color:var(--text-secondary); padding: var(--space-6) 0;">
          <i class="fa-solid fa-spinner fa-spin"></i> Loading call logs...
        </td>
      </tr>
    `;
  }

  /* --------------------------------------------------------------------
     Badges
     -------------------------------------------------------------------- */
  function languagePill(lang) {
    return `<span class="lang-pill">${escapeHtml(languageName(lang))}</span>`;
  }

  function sentimentBadge(sentiment) {
    const cls = sentiment === 'positive' ? 'positive' : sentiment === 'negative' ? 'negative' : 'neutral';
    const label = sentiment ? sentiment.charAt(0).toUpperCase() + sentiment.slice(1) : 'Unknown';
    return `<span class="sentiment-tag sentiment-${cls}-tag">${label}</span>`;
  }

  function statusBadge(status) {
    const cls = status === 'active' ? 'in-progress' : (status || 'completed');
    const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown';
    return `<span class="status-tag status-${cls}">${label}</span>`;
  }

  function formatDuration(sec) {
    sec = sec || 0;
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  /* --------------------------------------------------------------------
     Transcript modal
     -------------------------------------------------------------------- */
  function bindModal() {
    if (!el.modal) return;

    el.tbody.addEventListener('click', (e) => {
      const btn = e.target.closest('.view-transcript-btn');
      if (!btn) return;
      openTranscript(btn.dataset.id);
    });

    el.modalClose?.addEventListener('click', closeModal);
    el.modalCancel?.addEventListener('click', closeModal);
    el.modal.addEventListener('click', (e) => {
      if (e.target === el.modal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && el.modal.classList.contains('active')) closeModal();
    });
  }

  function openModal() { el.modal.classList.add('active'); }
  function closeModal() { el.modal.classList.remove('active'); }

  async function openTranscript(callId) {
    if (!callId) return;
    openModal();
    el.modalCallId.textContent = '…';
    if (el.modalMeta) el.modalMeta.innerHTML = '';
    el.modalBody.innerHTML = '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading transcript…</p></div>';

    try {
      const call = await window.VoxAPI.getCall(callId);
      el.modalCallId.textContent = `#${call.call_ref || call.id}`;
      if (el.modalFullView) el.modalFullView.href = `conversation.html?id=${encodeURIComponent(call.id)}`;

      if (el.modalMeta) {
        el.modalMeta.innerHTML = `
          <span><i class="fa-solid fa-language"></i> ${escapeHtml(languageName(call.language))}</span>
          <span><i class="fa-solid fa-clock"></i> ${formatDuration(call.duration_seconds)}</span>
          <span><i class="fa-solid fa-face-smile"></i> ${escapeHtml(call.sentiment || 'neutral')} sentiment</span>
        `;
      }

      renderTranscript(call.transcripts || []);
    } catch (err) {
      toast(err.message, 'error');
      el.modalBody.innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><p>Could not load this transcript.</p></div>';
    }
  }

  function renderTranscript(turns) {
    el.modalBody.innerHTML = '';

    if (!turns.length) {
      el.modalBody.innerHTML = '<div class="empty-state"><i class="fa-solid fa-comment-slash"></i><p>No transcript turns recorded for this call.</p></div>';
      return;
    }

    turns.forEach((turn) => {
      const role = turn.speaker === 'user' ? 'user' : 'ai';

      const turnEl = document.createElement('div');
      turnEl.className = `turn turn-${role}`;

      const avatarEl = document.createElement('div');
      avatarEl.className = 'turn-avatar';
      avatarEl.innerHTML = role === 'user' ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';

      const bubbleEl = document.createElement('div');
      bubbleEl.className = 'turn-bubble';

      const textEl = document.createElement('p');
      textEl.className = 'turn-text';
      textEl.textContent = turn.text;

      const metaEl = document.createElement('span');
      metaEl.className = 'turn-meta';
      const time = turn.created_at ? new Date(turn.created_at).toLocaleTimeString() : '';
      metaEl.textContent = role === 'ai'
        ? `${(turn.language || 'en').toUpperCase()} · ${turn.latency_ms ?? 0}ms`
        : time;

      bubbleEl.appendChild(textEl);
      bubbleEl.appendChild(metaEl);
      turnEl.appendChild(avatarEl);
      turnEl.appendChild(bubbleEl);
      el.modalBody.appendChild(turnEl);
    });
  }
})();