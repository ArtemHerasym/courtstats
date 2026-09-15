/* Verified charts only. Theme helpers are shared with dashboard.js; app.js
   remains the sole owner of theme preference and theme-change events. */
(() => {
    const charts = [];
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");

    const render = () => {
        while (charts.length) charts.pop().destroy();
        document.querySelectorAll("[data-report-chart]").forEach((element) => {
            const canvas = document.getElementById(element.dataset.reportChart);
            if (!canvas) return;
            canvas.parentElement.hidden = true;
            if (typeof Chart === "undefined") return;
            try {
                const visual = JSON.parse(element.textContent);
                if (!visual.labels?.length || !visual.datasets?.length || !visual.rows?.length) return;
                if (!["progression", "player", "comparison"].includes(visual.kind)) return;
                if (!visual.datasets.every((series) => series.data.length === visual.labels.length
                    && series.data.every((value) => value === null || Number.isFinite(value)))) return;
                const theme = getChartTheme();
                const horizontal = visual.kind === "player";
                const options = buildBaseOptions(theme);
                options.animation = motion.matches ? false : { duration: 200 };
                options.indexAxis = horizontal ? "y" : "x";
                options.scales = buildCartesianScales(theme, { xBeginAtZero: horizontal });
                options.scales[horizontal ? "x" : "y"].title = {
                    display: true, text: visual.units, color: theme.text,
                };
                if (visual.percentage) {
                    options.scales[horizontal ? "x" : "y"].max = 100;
                }
                options.plugins.legend.display = visual.datasets.length > 1;
                options.interaction.axis = horizontal ? "y" : "x";
                canvas.parentElement.hidden = false;
                charts.push(new Chart(canvas, {
                    type: visual.kind === "progression" ? "line" : "bar",
                    data: {
                        labels: visual.labels,
                        datasets: visual.datasets.map((series, index) => ({
                            label: series.label,
                            data: series.data,
                            backgroundColor: index % 2 ? theme.secondary : theme.primary,
                            borderColor: index % 2 ? theme.secondary : theme.primary,
                            borderWidth: 2,
                            borderDash: index % 2 ? [5, 4] : [],
                            pointStyle: index % 2 ? "rect" : "circle",
                            pointRadius: 3,
                            tension: 0,
                            spanGaps: false,
                        })),
                    },
                    options,
                }));
            } catch (error) {
                // The exact-value HTML table remains usable if charts fail.
                canvas.parentElement.hidden = true;
            }
        });
    };
    render();
    window.addEventListener("courtstats:themechange", render);
    motion.addEventListener("change", render);
})();
