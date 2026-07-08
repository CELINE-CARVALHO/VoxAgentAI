/* ==========================================================================
   VoxAgent AI - Call Logs
   Part 1 - Foundation
   ==========================================================================
*/

(function () {
    "use strict";

    let calls = [];
    let filteredCalls = [];

    let currentPage = 1;
    const pageSize = 10;

    const elements = {
        tbody: document.getElementById("callLogsBody"),
        badge: document.getElementById("callCountBadge"),
        empty: document.getElementById("callLogsEmpty"),

        prev: document.getElementById("paginationPrev"),
        next: document.getElementById("paginationNext"),
        pages: document.getElementById("paginationPages"),

        search: document.getElementById("callSearchInput"),
        language: document.getElementById("filterLanguage"),
        sentiment: document.getElementById("filterSentiment"),
        status: document.getElementById("filterStatus"),
        reset: document.getElementById("filterResetBtn"),
    };

    document.addEventListener("DOMContentLoaded", init);

    async function init() {

        if (!window.VoxAPI.isAuthenticated()) {
            location.href = "login.html";
            return;
        }

        bindPagination();

        await loadCalls();

    }

    async function loadCalls() {

        try {

            showLoading();

            calls = await VoxAPI.listCalls();

            filteredCalls = [...calls];

            renderTable();

        }

        catch (err) {

            console.error(err);

            VoxUtils.toast(err.message, "error");

        }

    }

    function renderTable() {

        elements.tbody.innerHTML = "";

        if (!filteredCalls.length) {

            elements.empty.hidden = false;

            elements.badge.textContent = "0 calls";

            return;

        }

        elements.empty.hidden = true;

        elements.badge.textContent =
            `${filteredCalls.length} calls`;

        const start = (currentPage - 1) * pageSize;

        const end = start + pageSize;

        filteredCalls
            .slice(start, end)
            .forEach(addRow);

        renderPagination();

    }

    function addRow(call) {

        const tr = document.createElement("tr");

        tr.dataset.callId = call.id;

        tr.innerHTML = `

<td class="cell-mono">#${call.id}</td>

<td>${languageBadge(call.language)}</td>

<td>${formatDuration(call.duration_seconds)}</td>

<td>${sentimentBadge(call.sentiment)}</td>

<td>${statusBadge(call.status)}</td>

<td>${formatDate(call.started_at)}</td>

<td>

<button
class="table-icon-btn view-transcript-btn"
data-id="${call.id}">

<i class="fa-solid fa-eye"></i>

</button>

</td>

`;

        elements.tbody.appendChild(tr);

    }

    function bindPagination() {

        elements.prev.addEventListener("click", () => {

            if (currentPage > 1) {

                currentPage--;

                renderTable();

            }

        });

        elements.next.addEventListener("click", () => {

            const maxPage =
                Math.ceil(filteredCalls.length / pageSize);

            if (currentPage < maxPage) {

                currentPage++;

                renderTable();

            }

        });

    }

    function renderPagination() {

        const maxPage =
            Math.ceil(filteredCalls.length / pageSize);

        elements.prev.disabled =
            currentPage === 1;

        elements.next.disabled =
            currentPage >= maxPage;

    }

    function showLoading() {

        elements.tbody.innerHTML = `

<tr>

<td colspan="7" style="text-align:center">

Loading call logs...

</td>

</tr>

`;

    }

    function languageBadge(lang) {

        return `<span class="lang-pill">${lang || "-"}</span>`;

    }

    function sentimentBadge(sentiment) {

        const cls =
            sentiment === "positive"
                ? "positive"
                : sentiment === "negative"
                ? "negative"
                : "neutral";

        return `

<span class="sentiment-tag sentiment-${cls}-tag">

${sentiment || "Unknown"}

</span>

`;

    }

    function statusBadge(status) {

        return `

<span class="status-tag status-${status}">

${status}

</span>

`;

    }

    function formatDuration(sec) {

        sec = sec || 0;

        const m = Math.floor(sec / 60);

        const s = sec % 60;

        return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;

    }

    function formatDate(date) {

        return new Date(date).toLocaleString();

    }

})();