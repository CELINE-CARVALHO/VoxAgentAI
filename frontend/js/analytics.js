/* ==========================================================================
   VoxAgent AI — Analytics Page
   Loads analytics from the backend and renders charts.
   Requires:
   - utils.js
   - api.js
   - charts.js
   - Chart.js
   ========================================================================== */

(function () {
    "use strict";

    let currentRange = "daily";

    const el = {
        totalCalls: document.getElementById("statTotalCalls"),
        avgDuration: document.getElementById("statAvgDurationAnalytics"),
        avgLatency: document.getElementById("statAvgLatency"),
        positiveSentiment: document.getElementById("statPositiveSentiment"),
        rangeTabs: document.querySelectorAll(".range-tab"),
    };

    document.addEventListener("DOMContentLoaded", init);

    async function init() {

        if (!window.VoxAPI.isAuthenticated()) {
            window.location.href = "login.html";
            return;
        }

        initRangeSelector();

        await loadDashboardStats();

        await loadCallVolume();

        await loadLanguages();

        await loadSentiment();

        await loadPerformance();

        // Will be enabled after backend endpoint exists
        // await loadTopIntents();

    }

    function initRangeSelector() {

        el.rangeTabs.forEach(btn => {

            btn.addEventListener("click", async () => {

                el.rangeTabs.forEach(b => b.classList.remove("active"));

                btn.classList.add("active");

                currentRange = btn.dataset.range;

                await loadCallVolume();

                await loadSentiment();

            });

        });

    }

    async function loadDashboardStats() {

        try {

            const perf = await window.VoxAPI.analyticsPerformance();

            el.totalCalls.textContent = perf.total_calls;

            el.avgLatency.textContent =
                `${Math.round(perf.avg_latency_ms)} ms`;

            el.avgDuration.textContent =
                formatDuration(perf.avg_duration_seconds);

        }

        catch (err) {

            window.VoxUtils.toast(err.message, "error");

        }

    }

    async function loadCallVolume() {

        try {

            const data =
                await window.VoxAPI.analyticsCalls(currentRange);

            window.VoxCharts.lineChart(
                "callVolumeChart",
                {
                    labels:
                        data.points.map(p => p.label),

                    datasets: [
                        {
                            label: "Calls",
                            data:
                                data.points.map(p => p.value)
                        }
                    ]
                }
            );

        }

        catch (err) {

            window.VoxUtils.toast(err.message, "error");

        }

    }

    async function loadLanguages() {

        try {

            const data =
                await window.VoxAPI.analyticsLanguages();

            window.VoxCharts.barChart(
                "languageBarChart",
                {
                    labels:
                        data.map(l => l.language),

                    datasets: [
                        {
                            label: "Calls",
                            data:
                                data.map(l => l.count)
                        }
                    ]
                }
            );

        }

        catch (err) {

            window.VoxUtils.toast(err.message, "error");

        }

    }

    async function loadSentiment() {

        try {

            const data =
                await window.VoxAPI.analyticsSentiment(currentRange);

            const positive =
                data.positive.reduce(
                    (sum, x) => sum + x.value,
                    0
                );

            const neutral =
                data.neutral.reduce(
                    (sum, x) => sum + x.value,
                    0
                );

            const negative =
                data.negative.reduce(
                    (sum, x) => sum + x.value,
                    0
                );

            const total =
                positive + neutral + negative;

            const pct =
                total
                    ? Math.round((positive / total) * 100)
                    : 0;

            el.positiveSentiment.textContent =
                `${pct}%`;

            window.VoxCharts.doughnutChart(
                "sentimentDonutChart",
                {
                    labels: [
                        "Positive",
                        "Neutral",
                        "Negative"
                    ],

                    datasets: [
                        {
                            data: [
                                positive,
                                neutral,
                                negative
                            ]
                        }
                    ]
                }
            );

        }

        catch (err) {

            window.VoxUtils.toast(err.message, "error");

        }

    }

    async function loadPerformance() {

        try {

            const perf =
                await window.VoxAPI.analyticsPerformance();

            window.VoxCharts.lineChart(
                "latencyLineChart",
                {
                    labels: ["Average"],

                    datasets: [
                        {
                            label: "Latency (ms)",
                            data: [perf.avg_latency_ms]
                        }
                    ]
                }
            );

            window.VoxCharts.lineChart(
                "durationLineChart",
                {
                    labels: ["Average"],

                    datasets: [
                        {
                            label: "Duration (sec)",

                            data: [
                                perf.avg_duration_seconds
                            ]
                        }
                    ]
                }
            );

        }

        catch (err) {

            window.VoxUtils.toast(err.message, "error");

        }

    }

    function formatDuration(seconds) {

        seconds = Math.round(seconds || 0);

        const m = Math.floor(seconds / 60);

        const s = seconds % 60;

        return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;

    }

})();

async function loadTopIntents() {

    const intents = await VoxAPI.analyticsIntents();

    const tbody = document.getElementById("topIntentsBody");

    tbody.innerHTML = "";

    intents.forEach(intent => {

        tbody.innerHTML += `
        <tr>
            <td>${intent.intent}</td>
            <td>${intent.count}</td>
            <td>${intent.avg_sentiment}</td>
            <td>${formatDuration(intent.avg_duration)}</td>
        </tr>`;
    });

}