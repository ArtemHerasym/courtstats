// ==========================================================
// CourtStats Season Dashboard
// ==========================================================

const dashboardCharts = [];


// ----------------------------------------------------------
// Utilities
// ----------------------------------------------------------

const getCssVariable = (name) => {
    return getComputedStyle(
        document.documentElement
    )
        .getPropertyValue(name)
        .trim();
};


const hexToRgba = (
    color,
    alpha
) => {
    if (!color.startsWith("#")) {
        return color;
    }

    let hex = color.slice(1);

    if (hex.length === 3) {
        hex = hex
            .split("")
            .map(character => character + character)
            .join("");
    }

    if (hex.length !== 6) {
        return color;
    }

    const red = parseInt(
        hex.slice(0, 2),
        16
    );

    const green = parseInt(
        hex.slice(2, 4),
        16
    );

    const blue = parseInt(
        hex.slice(4, 6),
        16
    );

    return (
        `rgba(${red}, ${green}, ${blue}, ${alpha})`
    );
};


const getChartTheme = () => {
    return {
        primary: getCssVariable(
            "--chart-primary"
        ),

        secondary: getCssVariable(
            "--chart-secondary"
        ),

        accent: getCssVariable(
            "--chart-accent"
        ),

        grid: getCssVariable(
            "--chart-grid"
        ),

        text: getCssVariable(
            "--chart-text"
        ),

        surface: getCssVariable(
            "--color-surface-raised"
        ),

        strongText: getCssVariable(
            "--color-text"
        ),

        success: getCssVariable(
            "--color-success"
        ),

        danger: getCssVariable(
            "--color-danger"
        ),
    };
};


const destroyDashboardCharts = () => {
    while (dashboardCharts.length > 0) {
        const chart = dashboardCharts.pop();

        chart.destroy();
    }
};


const registerChart = (chart) => {
    dashboardCharts.push(chart);

    return chart;
};


const buildBaseOptions = (
    theme
) => {
    return {
        responsive: true,
        maintainAspectRatio: false,

        interaction: {
            mode: "index",
            intersect: false,
        },

        plugins: {
            legend: {
                labels: {
                    color: theme.text,

                    usePointStyle: true,

                    pointStyle: "circle",

                    boxWidth: 8,
                    boxHeight: 8,

                    padding: 16,

                    font: {
                        size: 11,
                        weight: "600",
                    },
                },
            },

            tooltip: {
                backgroundColor:
                    theme.surface,

                titleColor:
                    theme.strongText,

                bodyColor:
                    theme.text,

                borderColor:
                    theme.grid,

                borderWidth: 1,

                padding: 11,

                displayColors: true,
            },
        },
    };
};


const buildCartesianScales = (
    theme,
    {
        xBeginAtZero = false,
        yBeginAtZero = true,
    } = {}
) => {
    return {
        x: {
            beginAtZero:
                xBeginAtZero,

            grid: {
                color:
                    hexToRgba(
                        theme.grid,
                        0.55
                    ),
            },

            border: {
                color: theme.grid,
            },

            ticks: {
                color: theme.text,

                font: {
                    size: 10,
                },
            },

            title: {
                color: theme.text,
            },
        },

        y: {
            beginAtZero:
                yBeginAtZero,

            grid: {
                color:
                    hexToRgba(
                        theme.grid,
                        0.55
                    ),
            },

            border: {
                color: theme.grid,
            },

            ticks: {
                color: theme.text,

                font: {
                    size: 10,
                },
            },

            title: {
                color: theme.text,
            },
        },
    };
};


// ----------------------------------------------------------
// Build all charts
// ----------------------------------------------------------

const buildDashboardCharts = () => {
    if (
        typeof Chart === "undefined"
    ) {
        return;
    }

    destroyDashboardCharts();

    const theme = getChartTheme();

    const baseOptions = (
        buildBaseOptions(theme)
    );


    // ======================================================
    // Main season data
    // ======================================================

    const chartDataElement = (
        document.getElementById(
            "season-chart-data"
        )
    );


    if (chartDataElement) {
        const chartData = JSON.parse(
            chartDataElement.textContent
        );


        // --------------------------------------------------
        // Scoring Trend
        // --------------------------------------------------

        const scoringTrendCanvas = (
            document.getElementById(
                "scoring-trend-chart"
            )
        );


        if (scoringTrendCanvas) {
            registerChart(
                new Chart(
                    scoringTrendCanvas,
                    {
                        type: "line",

                        data: {
                            labels:
                                chartData.game_labels,

                            datasets: [
                                {
                                    label:
                                        "Team Score",

                                    data:
                                        chartData.team_scores,

                                    borderColor:
                                        theme.primary,

                                    backgroundColor:
                                        hexToRgba(
                                            theme.primary,
                                            0.12
                                        ),

                                    pointBackgroundColor:
                                        theme.primary,

                                    pointBorderColor:
                                        theme.surface,

                                    pointBorderWidth: 2,

                                    tension: 0.3,

                                    pointRadius: 4,

                                    pointHoverRadius: 6,

                                    fill: true,
                                },
                            ],
                        },

                        options: {
                            ...baseOptions,

                            scales: {
                                ...buildCartesianScales(
                                    theme
                                ),

                                y: {
                                    ...buildCartesianScales(
                                        theme
                                    ).y,

                                    title: {
                                        display: true,
                                        text: "Points",
                                        color: theme.text,
                                    },
                                },
                            },
                        },
                    }
                )
            );
        }


        // --------------------------------------------------
        // Team vs Opponent
        // --------------------------------------------------

        const scoreComparisonCanvas = (
            document.getElementById(
                "score-comparison-chart"
            )
        );


        if (scoreComparisonCanvas) {
            registerChart(
                new Chart(
                    scoreComparisonCanvas,
                    {
                        type: "bar",

                        data: {
                            labels:
                                chartData.game_labels,

                            datasets: [
                                {
                                    label:
                                        "Team Score",

                                    data:
                                        chartData.team_scores,

                                    backgroundColor:
                                        hexToRgba(
                                            theme.primary,
                                            0.78
                                        ),

                                    borderColor:
                                        theme.primary,

                                    borderWidth: 1,

                                    borderRadius: 6,
                                },

                                {
                                    label:
                                        "Opponent Score",

                                    data:
                                        chartData.opponent_scores,

                                    backgroundColor:
                                        hexToRgba(
                                            theme.secondary,
                                            0.55
                                        ),

                                    borderColor:
                                        theme.secondary,

                                    borderWidth: 1,

                                    borderRadius: 6,
                                },
                            ],
                        },

                        options: {
                            ...baseOptions,

                            scales: {
                                ...buildCartesianScales(
                                    theme
                                ),

                                y: {
                                    ...buildCartesianScales(
                                        theme
                                    ).y,

                                    title: {
                                        display: true,
                                        text: "Points",
                                        color: theme.text,
                                    },
                                },
                            },
                        },
                    }
                )
            );
        }


        // --------------------------------------------------
        // Shooting Percentage Trends
        // --------------------------------------------------

        const shootingTrendCanvas = (
            document.getElementById(
                "shooting-trend-chart"
            )
        );


        if (shootingTrendCanvas) {
            const shootingBase = {
                tension: 0.3,
                pointRadius: 3,
                pointHoverRadius: 5,
                pointBorderWidth: 2,
                pointBorderColor:
                    theme.surface,
            };


            registerChart(
                new Chart(
                    shootingTrendCanvas,
                    {
                        type: "line",

                        data: {
                            labels:
                                chartData.game_labels,

                            datasets: [
                                {
                                    ...shootingBase,

                                    label: "FG%",

                                    data:
                                        chartData.fg_percentages,

                                    borderColor:
                                        theme.primary,

                                    pointBackgroundColor:
                                        theme.primary,
                                },

                                {
                                    ...shootingBase,

                                    label: "2PT%",

                                    data:
                                        chartData.two_point_percentages,

                                    borderColor:
                                        theme.secondary,

                                    pointBackgroundColor:
                                        theme.secondary,
                                },

                                {
                                    ...shootingBase,

                                    label: "3PT%",

                                    data:
                                        chartData.three_point_percentages,

                                    borderColor:
                                        theme.accent,

                                    pointBackgroundColor:
                                        theme.accent,
                                },

                                {
                                    ...shootingBase,

                                    label: "FT%",

                                    data:
                                        chartData.free_throw_percentages,

                                    borderColor:
                                        theme.success,

                                    pointBackgroundColor:
                                        theme.success,
                                },
                            ],
                        },

                        options: {
                            ...baseOptions,

                            scales: {
                                ...buildCartesianScales(
                                    theme
                                ),

                                y: {
                                    ...buildCartesianScales(
                                        theme
                                    ).y,

                                    min: 0,
                                    max: 1,

                                    title: {
                                        display: true,
                                        text: "Percentage",
                                        color: theme.text,
                                    },

                                    ticks: {
                                        color: theme.text,

                                        callback: (
                                            value
                                        ) => {
                                            return (
                                                value * 100
                                            ) + "%";
                                        },
                                    },
                                },
                            },

                            plugins: {
                                ...baseOptions.plugins,

                                tooltip: {
                                    ...baseOptions
                                        .plugins
                                        .tooltip,

                                    callbacks: {
                                        label: (
                                            context
                                        ) => {
                                            if (
                                                context.raw
                                                === null
                                            ) {
                                                return (
                                                    context
                                                        .dataset
                                                        .label
                                                    + ": —"
                                                );
                                            }

                                            return (
                                                context
                                                    .dataset
                                                    .label
                                                + ": "
                                                + (
                                                    context.raw
                                                    * 100
                                                ).toFixed(1)
                                                + "%"
                                            );
                                        },
                                    },
                                },
                            },
                        },
                    }
                )
            );
        }
    }


    // ======================================================
    // Win/Loss and Venue Comparisons
    // ======================================================

    const comparisonDataElement = (
        document.getElementById(
            "season-comparison-data"
        )
    );


    if (comparisonDataElement) {
        const comparisonData = JSON.parse(
            comparisonDataElement.textContent
        );


        const wins = (
            comparisonData.by_result.WIN
        );

        const losses = (
            comparisonData.by_result.LOSS
        );


        // --------------------------------------------------
        // Win vs Loss
        // --------------------------------------------------

        const resultComparisonCanvas = (
            document.getElementById(
                "result-comparison-chart"
            )
        );


        if (resultComparisonCanvas) {
            registerChart(
                new Chart(
                    resultComparisonCanvas,
                    {
                        type: "bar",

                        data: {
                            labels: [
                                `Wins (${wins.games_played})`,
                                `Losses (${losses.games_played})`,
                            ],

                            datasets: [
                                {
                                    label: "PPG",

                                    data: [
                                        wins.points_per_game,
                                        losses.points_per_game,
                                    ],

                                    backgroundColor:
                                        hexToRgba(
                                            theme.primary,
                                            0.8
                                        ),

                                    borderRadius: 6,
                                },

                                {
                                    label: "RPG",

                                    data: [
                                        wins.rebounds_per_game,
                                        losses.rebounds_per_game,
                                    ],

                                    backgroundColor:
                                        hexToRgba(
                                            theme.secondary,
                                            0.68
                                        ),

                                    borderRadius: 6,
                                },

                                {
                                    label: "APG",

                                    data: [
                                        wins.assists_per_game,
                                        losses.assists_per_game,
                                    ],

                                    backgroundColor:
                                        hexToRgba(
                                            theme.accent,
                                            0.78
                                        ),

                                    borderRadius: 6,
                                },

                                {
                                    label: "TO/G",

                                    data: [
                                        wins.turnovers_per_game,
                                        losses.turnovers_per_game,
                                    ],

                                    backgroundColor:
                                        hexToRgba(
                                            theme.danger,
                                            0.65
                                        ),

                                    borderRadius: 6,
                                },
                            ],
                        },

                        options: {
                            ...baseOptions,

                            scales:
                                buildCartesianScales(
                                    theme
                                ),
                        },
                    }
                )
            );
        }


        // --------------------------------------------------
        // Performance by Venue
        // --------------------------------------------------

        const home = (
            comparisonData.by_venue.HOME
        );

        const away = (
            comparisonData.by_venue.AWAY
        );

        const neutral = (
            comparisonData.by_venue.NEUTRAL
        );


        const venueComparisonCanvas = (
            document.getElementById(
                "venue-comparison-chart"
            )
        );


        if (venueComparisonCanvas) {
            registerChart(
                new Chart(
                    venueComparisonCanvas,
                    {
                        type: "bar",

                        data: {
                            labels: [
                                `Home (${home.games_played})`,
                                `Away (${away.games_played})`,
                                `Neutral (${neutral.games_played})`,
                            ],

                            datasets: [
                                {
                                    label: "PPG",

                                    data: [
                                        home.points_per_game,
                                        away.points_per_game,
                                        neutral.points_per_game,
                                    ],

                                    backgroundColor:
                                        hexToRgba(
                                            theme.primary,
                                            0.8
                                        ),

                                    borderRadius: 6,
                                },

                                {
                                    label: "RPG",

                                    data: [
                                        home.rebounds_per_game,
                                        away.rebounds_per_game,
                                        neutral.rebounds_per_game,
                                    ],

                                    backgroundColor:
                                        hexToRgba(
                                            theme.secondary,
                                            0.68
                                        ),

                                    borderRadius: 6,
                                },

                                {
                                    label: "APG",

                                    data: [
                                        home.assists_per_game,
                                        away.assists_per_game,
                                        neutral.assists_per_game,
                                    ],

                                    backgroundColor:
                                        hexToRgba(
                                            theme.accent,
                                            0.78
                                        ),

                                    borderRadius: 6,
                                },

                                {
                                    label: "TO/G",

                                    data: [
                                        home.turnovers_per_game,
                                        away.turnovers_per_game,
                                        neutral.turnovers_per_game,
                                    ],

                                    backgroundColor:
                                        hexToRgba(
                                            theme.danger,
                                            0.65
                                        ),

                                    borderRadius: 6,
                                },
                            ],
                        },

                        options: {
                            ...baseOptions,

                            scales:
                                buildCartesianScales(
                                    theme
                                ),
                        },
                    }
                )
            );
        }
    }


    // ======================================================
    // Player Scoring Comparison
    // ======================================================

    const playerScoringDataElement = (
        document.getElementById(
            "season-player-scoring-data"
        )
    );


    if (playerScoringDataElement) {
        const playerScoringData = JSON.parse(
            playerScoringDataElement.textContent
        );


        const playerScoringCanvas = (
            document.getElementById(
                "player-scoring-chart"
            )
        );


        if (playerScoringCanvas) {
            registerChart(
                new Chart(
                    playerScoringCanvas,
                    {
                        type: "bar",

                        data: {
                            labels:
                                playerScoringData.map(
                                    player =>
                                        player.player_name
                                ),

                            datasets: [
                                {
                                    label: "PPG",

                                    data:
                                        playerScoringData.map(
                                            player =>
                                                player.points_per_game
                                        ),

                                    backgroundColor:
                                        hexToRgba(
                                            theme.primary,
                                            0.78
                                        ),

                                    borderColor:
                                        theme.primary,

                                    borderWidth: 1,

                                    borderRadius: 6,
                                },
                            ],
                        },

                        options: {
                            ...baseOptions,

                            indexAxis: "y",

                            scales: {
                                x: {
                                    ...buildCartesianScales(
                                        theme,
                                        {
                                            xBeginAtZero:
                                                true,
                                        }
                                    ).x,

                                    beginAtZero: true,

                                    title: {
                                        display: true,

                                        text:
                                            "Points Per Game",

                                        color:
                                            theme.text,
                                    },
                                },

                                y: {
                                    ...buildCartesianScales(
                                        theme
                                    ).y,

                                    beginAtZero: false,
                                },
                            },

                            plugins: {
                                ...baseOptions.plugins,

                                legend: {
                                    display: false,
                                },

                                tooltip: {
                                    ...baseOptions
                                        .plugins
                                        .tooltip,

                                    callbacks: {
                                        label: (
                                            context
                                        ) => {
                                            return (
                                                Number(
                                                    context.raw
                                                ).toFixed(1)
                                                + " PPG"
                                            );
                                        },
                                    },
                                },
                            },
                        },
                    }
                )
            );
        }
    }
};


// ----------------------------------------------------------
// Initial render
// ----------------------------------------------------------

buildDashboardCharts();


// ----------------------------------------------------------
// CourtStats light/dark theme integration
// ----------------------------------------------------------

window.addEventListener(
    "courtstats:themechange",
    () => {
        buildDashboardCharts();
    }
);