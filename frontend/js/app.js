/* ==========================================================================
   VoxAgent AI — App Shell Script
   Sidebar collapse/expand, mobile slide-in nav, theme toggle, active-link
   highlighting. Loaded on every page — must run before page-specific JS.
   ========================================================================== */
(function () {
  'use strict';

  const STORAGE_KEYS = {
    theme: 'voxagent-theme',
    collapsed: 'voxagent-sidebar-collapsed'
  };

  const MOBILE_BREAKPOINT = 900; // px — matches responsive.css breakpoint

  /* ------------------------------------------------------------------------
     1. ELEMENT CACHE
     ------------------------------------------------------------------------ */
  const el = {
    body: document.body,
    appShell: document.querySelector('.app-shell'),
    sidebar: document.getElementById('sidebar'),
    hamburger: document.getElementById('sidebarHamburger'),
    themeToggle: document.getElementById('themeToggle'),
    sidebarLinks: document.querySelectorAll('.sidebar-link')
  };

  // Guard: if this page doesn't have the app shell (unlikely), bail quietly.
  if (!el.sidebar || !el.appShell) return;

  let backdrop = document.getElementById('sidebarBackdrop');
  if (!backdrop) {
    backdrop = document.createElement('div');
    backdrop.id = 'sidebarBackdrop';
    backdrop.className = 'sidebar-backdrop';
    document.body.appendChild(backdrop);
  }

  const state = {
    collapsed: false,
    mobileOpen: false
  };

  /* ------------------------------------------------------------------------
     2. THEME (dark/light)
     ------------------------------------------------------------------------ */
  function applyTheme(theme) {
    const isDark = theme === 'dark';
    el.body.classList.toggle('dark-mode', isDark);
    el.body.classList.toggle('light-mode', !isDark);

    if (el.themeToggle) {
      const icon = el.themeToggle.querySelector('i');
      if (icon) {
        icon.className = isDark ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
      }
      el.themeToggle.setAttribute(
        'aria-label',
        isDark ? 'Switch to light mode' : 'Switch to dark mode'
      );
    }
  }

  function getStoredTheme() {
    const stored = localStorage.getItem(STORAGE_KEYS.theme);
    if (stored === 'dark' || stored === 'light') return stored;

    // Fall back to the class already present on <body> (server-rendered default),
    // then to the OS preference, then default to dark (VoxAgent AI's brand default).
    if (el.body.classList.contains('light-mode')) return 'light';
    if (el.body.classList.contains('dark-mode')) return 'dark';
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
    return 'dark';
  }

  function toggleTheme() {
    const current = el.body.classList.contains('dark-mode') ? 'dark' : 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    localStorage.setItem(STORAGE_KEYS.theme, next);
  }

  /* ------------------------------------------------------------------------
     3. SIDEBAR — DESKTOP COLLAPSE
     ------------------------------------------------------------------------ */
  function applyCollapsed(collapsed) {
    state.collapsed = collapsed;
    el.appShell.classList.toggle('sidebar-collapsed', collapsed);
    if (el.hamburger) {
      el.hamburger.setAttribute('aria-expanded', String(!collapsed));
    }
  }

  function toggleCollapsed() {
    const next = !state.collapsed;
    applyCollapsed(next);
    localStorage.setItem(STORAGE_KEYS.collapsed, String(next));
  }

  /* ------------------------------------------------------------------------
     4. SIDEBAR — MOBILE SLIDE-IN
     ------------------------------------------------------------------------ */
  function isMobileViewport() {
    return window.innerWidth <= MOBILE_BREAKPOINT;
  }

  function openMobileSidebar() {
    state.mobileOpen = true;
    el.sidebar.classList.add('sidebar-mobile-open');
    backdrop.classList.add('active');
    el.body.classList.add('sidebar-mobile-locked'); // optional scroll-lock hook
    if (el.hamburger) el.hamburger.setAttribute('aria-expanded', 'true');
  }

  function closeMobileSidebar() {
    state.mobileOpen = false;
    el.sidebar.classList.remove('sidebar-mobile-open');
    backdrop.classList.remove('active');
    el.body.classList.remove('sidebar-mobile-locked');
    if (el.hamburger) el.hamburger.setAttribute('aria-expanded', 'false');
  }

  function toggleMobileSidebar() {
    if (state.mobileOpen) {
      closeMobileSidebar();
    } else {
      openMobileSidebar();
    }
  }

  /* ------------------------------------------------------------------------
     5. HAMBURGER — routes to the right behavior for viewport size
     ------------------------------------------------------------------------ */
  function handleHamburgerClick() {
    if (isMobileViewport()) {
      toggleMobileSidebar();
    } else {
      toggleCollapsed();
    }
  }

  // If the viewport crosses the breakpoint (e.g. rotating a tablet, resizing
  // a window), make sure we're not stuck in a broken half-open state.
  function handleResize() {
    if (!isMobileViewport() && state.mobileOpen) {
      closeMobileSidebar();
    }
  }

  /* ------------------------------------------------------------------------
     6. ACTIVE LINK HIGHLIGHTING
     ------------------------------------------------------------------------ */
  function highlightActiveLink() {
    const currentPage = (window.location.pathname.split('/').pop() || 'dashboard.html');

    el.sidebarLinks.forEach((link) => {
      const href = link.getAttribute('href');
      link.classList.toggle('active', href === currentPage);
    });
  }

  /* ------------------------------------------------------------------------
     7. INIT
     ------------------------------------------------------------------------ */
  function init() {
    applyTheme(getStoredTheme());

    const storedCollapsed = localStorage.getItem(STORAGE_KEYS.collapsed) === 'true';
    applyCollapsed(storedCollapsed);

    highlightActiveLink();

    if (el.hamburger) {
      el.hamburger.addEventListener('click', handleHamburgerClick);
    }
    if (el.themeToggle) {
      el.themeToggle.addEventListener('click', toggleTheme);
    }

    backdrop.addEventListener('click', closeMobileSidebar);

    // Close the mobile sidebar automatically after navigating
    el.sidebarLinks.forEach((link) => {
      link.addEventListener('click', () => {
        if (isMobileViewport()) closeMobileSidebar();
      });
    });

    // Escape key closes the mobile sidebar
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && state.mobileOpen) closeMobileSidebar();
    });

    window.addEventListener('resize', handleResize);
  }

  document.addEventListener('DOMContentLoaded', init);
})();