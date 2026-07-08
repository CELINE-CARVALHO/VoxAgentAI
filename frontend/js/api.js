/* ==========================================================================
   VoxAgent AI — API Client
   Thin fetch wrapper around the FastAPI backend. Handles JWT storage,
   auth headers, and consistent error surfacing via VoxUtils.toast.
   Loaded on every page, after utils.js and before page-specific scripts.
   ========================================================================== */
(function (global) {
  'use strict';

  // Change this if the backend runs elsewhere (e.g. a deployed URL).
  const API_BASE_URL = 'http://localhost:8000';
  const TOKEN_KEY = 'voxagent-token';

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setToken(token) {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  }

  function isAuthenticated() {
    return !!getToken();
  }

  async function request(path, { method = 'GET', body, isForm = false, auth = true } = {}) {
    const headers = {};
    if (!isForm) headers['Content-Type'] = 'application/json';
    if (auth) {
      const token = getToken();
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }

    let res;
    try {
      res = await fetch(`${API_BASE_URL}${path}`, {
        method,
        headers,
        body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
      });
    } catch (networkErr) {
      throw new Error('Could not reach the VoxAgent AI backend. Is it running?');
    }

    if (res.status === 401) {
      setToken(null);
      window.location.href = 'login.html';
      throw new Error('Session expired. Please log in again.');
    }

    if (res.status === 204) return null;

    const contentType = res.headers.get('content-type') || '';
    const payload = contentType.includes('application/json') ? await res.json() : await res.text();

    if (!res.ok) {
      const detail = (payload && payload.detail) || res.statusText || 'Request failed';
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }

    return payload;
  }

  const VoxAPI = {
    // ---- auth ----
    async register({ email, password, full_name }) {
      const data = await request('/api/auth/register', { method: 'POST', body: { email, password, full_name }, auth: false });
      setToken(data.access_token);
      return data.user;
    },
    async login({ email, password }) {
      const data = await request('/api/auth/login', { method: 'POST', body: { email, password }, auth: false });
      setToken(data.access_token);
      return data.user;
    },
    logout() {
      setToken(null);
      window.location.href = 'login.html';
    },
    me() {
      return request('/api/auth/me');
    },
    isAuthenticated,

    // ---- dashboard ----
    dashboardStats() { return request('/api/dashboard/stats'); },
    dashboardStatus() { return request('/api/dashboard/status'); },

    // ---- calls (live + logs) ----
    startCall(payload = {}) { return request('/api/calls/start', { method: 'POST', body: payload }); },
    sendMessage(callId, text) { return request(`/api/calls/${callId}/message`, { method: 'POST', body: { text } }); },
    endCall(callId) { return request(`/api/calls/${callId}/end`, { method: 'POST' }); },
    getCall(callId) { return request(`/api/calls/${callId}`); },
    listCalls(params = {}) {
      const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== ''));
      return request(`/api/calls?${qs.toString()}`);
    },
    deleteCall(callId) { return request(`/api/calls/${callId}`, { method: 'DELETE' }); },

    // ---- knowledge base ----
    uploadDocument(file) {
      const form = new FormData();
      form.append('file', file);
      return request('/api/knowledge/upload', { method: 'POST', body: form, isForm: true });
    },
    listDocuments(params = {}) {
      const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== ''));
      return request(`/api/knowledge?${qs.toString()}`);
    },
    getDocument(docId) { return request(`/api/knowledge/${docId}`); },
    deleteDocument(docId) { return request(`/api/knowledge/${docId}`, { method: 'DELETE' }); },

    // ---- analytics ----
    analyticsCalls(range = 'daily') { return request(`/api/analytics/calls?range=${range}`); },
    analyticsLanguages() { return request('/api/analytics/languages'); },
    analyticsSentiment(range = 'daily') { return request(`/api/analytics/sentiment?range=${range}`); },
    analyticsPerformance() { return request('/api/analytics/performance'); },

    // ---- settings / profile ----
    getSettings() { return request('/api/settings'); },
    updateSettings(preferences) { return request('/api/settings', { method: 'PUT', body: { preferences } }); },
    getProfile() { return request('/api/profile'); },
    updateProfile(payload) { return request('/api/profile', { method: 'PUT', body: payload }); },
  };

  global.VoxAPI = VoxAPI;
})(window);