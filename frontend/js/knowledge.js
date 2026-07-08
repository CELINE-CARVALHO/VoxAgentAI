/* ==========================================================================
   VoxAgent AI — Knowledge Base Page Logic
   Drag-and-drop upload, list rendering with search/filter, delete with
   confirmation. Requires: utils.js, api.js — loaded before this file.
   ========================================================================== */
(function () {
  'use strict';

  const { toast, formatBytes, formatDate, debounce, escapeHtml } = window.VoxUtils;

  const el = {
    dropzone: document.getElementById('dropzone'),
    fileInput: document.getElementById('fileInput'),
    docList: document.getElementById('documentList'),
    searchInput: document.getElementById('kbSearchInput'),
    statusFilter: document.getElementById('kbStatusFilter'),
    emptyState: document.getElementById('kbEmptyState'),
  };

  const STATUS_META = {
    ready: { label: 'Ready', className: 'status-ready' },
    processing: { label: 'Processing', className: 'status-processing' },
    failed: { label: 'Failed', className: 'status-failed' },
  };

  const FILE_ICONS = { pdf: 'fa-file-pdf', docx: 'fa-file-word', txt: 'fa-file-lines', md: 'fa-file-lines', csv: 'fa-file-csv' };

  function docRowHtml(doc) {
    const status = STATUS_META[doc.status] || STATUS_META.processing;
    return `
      <div class="table-row" data-id="${doc.id}">
        <div class="table-cell doc-name-cell">
          <i class="fa-solid ${FILE_ICONS[doc.file_type] || 'fa-file'}"></i>
          <span>${escapeHtml(doc.filename)}</span>
        </div>
        <div class="table-cell">${doc.file_type.toUpperCase()}</div>
        <div class="table-cell">${formatBytes(doc.size_bytes)}</div>
        <div class="table-cell"><span class="badge ${status.className}">${status.label}</span></div>
        <div class="table-cell">${formatDate(doc.uploaded_at)}</div>
        <div class="table-cell">
          <button class="btn-icon btn-delete-doc" title="Delete" data-id="${doc.id}">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>`;
  }

  async function refreshList() {
    try {
      const params = {
        search: el.searchInput ? el.searchInput.value.trim() : '',
        status: el.statusFilter ? el.statusFilter.value : '',
      };
      const data = await window.VoxAPI.listDocuments(params);

      if (!el.docList) return;

      if (!data.items.length) {
        el.docList.innerHTML = '';
        if (el.emptyState) el.emptyState.classList.remove('hidden');
        return;
      }
      if (el.emptyState) el.emptyState.classList.add('hidden');
      el.docList.innerHTML = data.items.map(docRowHtml).join('');

      el.docList.querySelectorAll('.btn-delete-doc').forEach((btn) => {
        btn.addEventListener('click', () => handleDelete(btn.dataset.id));
      });
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  async function handleDelete(docId) {
    if (!confirm('Delete this document? This cannot be undone.')) return;
    try {
      await window.VoxAPI.deleteDocument(docId);
      toast('Document deleted', 'success');
      refreshList();
    } catch (err) {
      toast(err.message, 'error');
    }
  }

  async function uploadFiles(fileList) {
    const files = Array.from(fileList);
    for (const file of files) {
      try {
        toast(`Uploading ${file.name}…`, 'info', 2000);
        await window.VoxAPI.uploadDocument(file);
        toast(`${file.name} uploaded`, 'success');
      } catch (err) {
        toast(`${file.name} failed: ${err.message}`, 'error');
      }
    }
    refreshList();
  }

  function initDropzone() {
    if (!el.dropzone || !el.fileInput) return;

    el.dropzone.addEventListener('click', () => el.fileInput.click());
    el.fileInput.addEventListener('change', (e) => {
      if (e.target.files.length) uploadFiles(e.target.files);
      e.target.value = '';
    });

    ['dragenter', 'dragover'].forEach((evt) => {
      el.dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        el.dropzone.classList.add('dragover');
      });
    });
    ['dragleave', 'drop'].forEach((evt) => {
      el.dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        el.dropzone.classList.remove('dragover');
      });
    });
    el.dropzone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
    });
  }

  function init() {
    initDropzone();
    refreshList();

    if (el.searchInput) el.searchInput.addEventListener('input', debounce(refreshList, 300));
    if (el.statusFilter) el.statusFilter.addEventListener('change', refreshList);
  }

  document.addEventListener('DOMContentLoaded', init);
})();