/* ==========================================================================
   VoxAgent AI — app.js
   Cross-page shell behavior: auth guard, sidebar collapse (desktop) /
   mobile slide-in, theme toggle (dark/light, persisted), and active nav
   link highlighting.
   Loaded on every page, after utils.js and api.js, before page-specific
   scripts (e.g. calls.js, knowledge.js, analytics.js).
   ========================================================================== */
(function () {
  'use strict';

  /* ------------------------------------------------------------------------
     0. AUTH GUARD — redirect unauthenticated visitors away from protected
     pages before any layout or data renders. Runs first and returns early
     so nothing else in this file wires up on a page we're navigating away
     from. Public pages that don't load api.js (e.g. the landing page)
     skip this safely since window.VoxAPI is undefined there.
     ------------------------------------------------------------------------ */
  if (typeof window.VoxAPI !== 'undefined' && !window.VoxAPI.isAuthenticated()) {
    window.location.href = 'login.html';
    return;
  }

  const THEME_KEY = 'voxagent-theme';
  const SIDEBAR_KEY = 'voxagent-sidebar-collapsed';

  const body = document.body;
  const appShell = document.querySelector('.app-shell');
  const sidebar = document.getElementById('sidebar');
  const hamburgerBtn = document.getElementById('sidebarHamburger');
  const themeBtn = document.getElementById('themeToggle');

  const MOBILE_BREAKPOINT = 900; // matches the CSS breakpoint that shows .sidebar-hamburger

  function isMobile() {
    return window.innerWidth <= MOBILE_BREAKPOINT;
  }

  /* ------------------------------------------------------------------------
     1. SIDEBAR — collapse (desktop) or slide-in overlay (mobile)
     ------------------------------------------------------------------------ */
  function applyStoredSidebarState() {
    if (!appShell || isMobile()) return;
    const collapsed = localStorage.getItem(SIDEBAR_KEY) === '1';
    appShell.classList.toggle('sidebar-collapsed', collapsed);
  }

  function toggleSidebar() {
    if (isMobile()) {
      if (!sidebar) return;
      const open = sidebar.classList.toggle('sidebar-mobile-open');
      hamburgerBtn?.setAttribute('aria-expanded', String(open));
    } else {
      if (!appShell) return;
      const collapsed = appShell.classList.toggle('sidebar-collapsed');
      localStorage.setItem(SIDEBAR_KEY, collapsed ? '1' : '0');
      hamburgerBtn?.setAttribute('aria-expanded', String(!collapsed));
    }
  }

  // Tapping outside the sidebar closes it on mobile
  document.addEventListener('click', (e) => {
    if (!isMobile() || !sidebar) return;
    if (!sidebar.classList.contains('sidebar-mobile-open')) return;
    if (sidebar.contains(e.target) || e.target === hamburgerBtn || hamburgerBtn?.contains(e.target)) return;
    sidebar.classList.remove('sidebar-mobile-open');
    hamburgerBtn?.setAttribute('aria-expanded', 'false');
  });

  // Re-evaluate collapse state on resize (e.g. rotating a tablet, or resizing a browser window)
  window.addEventListener('resize', window.VoxUtils.debounce(() => {
    if (isMobile()) {
      appShell?.classList.remove('sidebar-collapsed');
    } else {
      sidebar?.classList.remove('sidebar-mobile-open');
      applyStoredSidebarState();
    }
  }, 150));

  hamburgerBtn?.addEventListener('click', toggleSidebar);

  /* ------------------------------------------------------------------------
     2. THEME TOGGLE — dark/light, persisted in localStorage
     ------------------------------------------------------------------------ */
  function updateThemeIcon(theme) {
    if (!themeBtn) return;
    const icon = themeBtn.querySelector('i');
    if (!icon) return;
    icon.className = theme === 'dark-mode' ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
  }

  function applyStoredTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    const theme = stored === 'light-mode' || stored === 'dark-mode'
      ? stored
      : (body.classList.contains('light-mode') ? 'light-mode' : 'dark-mode');

    body.classList.remove('dark-mode', 'light-mode');
    body.classList.add(theme);
    updateThemeIcon(theme);
  }

  function toggleTheme() {
    const isDark = body.classList.contains('dark-mode');
    const nextTheme = isDark ? 'light-mode' : 'dark-mode';
    body.classList.remove('dark-mode', 'light-mode');
    body.classList.add(nextTheme);
    localStorage.setItem(THEME_KEY, nextTheme);
    updateThemeIcon(nextTheme);
  }

  themeBtn?.addEventListener('click', toggleTheme);

  /* ------------------------------------------------------------------------
     3. ACTIVE NAV LINK (fallback for any page missing the .active class)
     ------------------------------------------------------------------------ */
  function markActiveNavLink() {
    const currentPage = window.location.pathname.split('/').pop() || 'dashboard.html';
    document.querySelectorAll('.sidebar-link').forEach((link) => {
      const href = link.getAttribute('href');
      link.classList.toggle('active', href === currentPage);
    });
  }

  /* ------------------------------------------------------------------------
     4. INIT
     ------------------------------------------------------------------------ */
  applyStoredTheme();
  applyStoredSidebarState();
  markActiveNavLink();
})();