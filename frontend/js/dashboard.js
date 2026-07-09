/* ==========================================================================
   VoxAgent AI
   Dashboard Controller
   Part 1 - Foundation
   ========================================================================== */

(() => {
    "use strict";

    const REFRESH_INTERVAL = 30000; // 30 seconds

    let refreshTimer = null;

    const DOM = {
        totalCalls: document.getElementById("statTotalCalls"),
        activeCalls: document.getElementById("statActiveCalls"),
        completedCalls: document.getElementById("statCompletedCalls"),
        avgDuration: document.getElementById("statAvgDuration"),
        avgLatency: document.getElementById("statAvgLatency"),
        documents: document.getElementById("statDocuments"),
        languages: document.getElementById("statLanguages"),

        backendStatus: document.getElementById("backendStatus"),
        databaseStatus: document.getElementById("databaseStatus"),
        llmStatus: document.getElementById("llmStatus"),
        kbStatus: document.getElementById("kbStatus"),

        recentCalls: document.getElementById("recentCallsBody"),

        refreshBadge: document.getElementById("dashboardUpdatedBadge"),
    };

    document.addEventListener("DOMContentLoaded", init);

    async function init() {

        if (!window.VoxAPI.isAuthenticated()) {
            location.href = "login.html";
            return;
        }

        await refreshDashboard();

        startAutoRefresh();
    }

    async function refreshDashboard() {

        try {

            showLoading();

            await Promise.all([
                loadDashboardStats(),
                loadSystemStatus(),
                loadRecentCalls(),
            ]);

            updateTimestamp();

        }

        catch (err) {

            console.error(err);

            VoxUtils.toast(err.message, "error");

        }

    }

    async function loadDashboardStats() {

        const stats = await VoxAPI.dashboardStats();

        setText(DOM.totalCalls, stats.total_calls);

        setText(DOM.activeCalls, stats.active_calls);

        setText(DOM.completedCalls, stats.completed_calls);

        setText(
            DOM.avgDuration,
            formatDuration(stats.avg_duration_seconds)
        );

        setText(
            DOM.avgLatency,
            `${Math.round(stats.avg_latency_ms)} ms`
        );

        setText(DOM.documents, stats.documents);

        setText(DOM.languages, stats.languages);
    }

    async function loadSystemStatus() {

        const status = await VoxAPI.dashboardStatus();

        updateStatus(DOM.backendStatus, status.backend);

        updateStatus(DOM.databaseStatus, status.database);

        updateStatus(DOM.llmStatus, status.llm_engine);

        updateStatus(DOM.kbStatus, status.knowledge_base);
    }

    async function loadRecentCalls() {

        const response = await VoxAPI.listCalls({
            page: 1,
            page_size: 5
        });

        renderRecentCalls(response.items);

    }

    function renderRecentCalls(calls) {

        if (!DOM.recentCalls) return;

        DOM.recentCalls.innerHTML = "";

        if (!calls.length) {

            DOM.recentCalls.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">
                        No recent calls
                    </td>
                </tr>
            `;

            return;
        }

        calls.forEach(call => {

            DOM.recentCalls.insertAdjacentHTML(
                "beforeend",
                buildCallRow(call)
            );

        });

    }

    function buildCallRow(call) {

        return `
<tr>

<td>#${call.call_ref ?? call.id}</td>

<td>${call.language ?? "-"}</td>

<td>${call.sentiment ?? "-"}</td>

<td>${formatDuration(call.duration_seconds)}</td>

<td>${call.status}</td>

<td>${formatDate(call.started_at)}</td>

</tr>
`;

    }

    function showLoading() {

        [
            DOM.totalCalls,
            DOM.activeCalls,
            DOM.completedCalls,
            DOM.avgDuration,
            DOM.avgLatency,
            DOM.documents,
            DOM.languages
        ].forEach(el => {

            if (el)
                el.textContent = "...";

        });

    }

    function updateStatus(element, status) {

        if (!element) return;

        element.textContent = status;

        element.classList.remove(
            "online",
            "offline",
            "warning"
        );

        switch (status) {

            case "online":
                element.classList.add("online");
                break;

            case "offline":
                element.classList.add("offline");
                break;

            default:
                element.classList.add("warning");

        }

    }

    function updateTimestamp() {

        if (!DOM.refreshBadge) return;

        DOM.refreshBadge.innerHTML = `
<i class="fa-solid fa-rotate"></i>

Updated ${new Date().toLocaleTimeString()}
`;

    }

    function startAutoRefresh() {

        refreshTimer = setInterval(
            refreshDashboard,
            REFRESH_INTERVAL
        );

    }

    function setText(el, value) {

        if (el)
            el.textContent = value;

    }

    function formatDuration(sec) {

        sec = Math.round(sec || 0);

        const m = Math.floor(sec / 60);

        const s = sec % 60;

        return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;

    }

    function formatDate(date) {

        return new Date(date).toLocaleString();

    }

})();