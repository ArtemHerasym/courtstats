const chartDataElement = document.getElementById(
    "season-chart-data"
);

if (chartDataElement) {
    const chartData = JSON.parse(
        chartDataElement.textContent
    );


    // --------------------------------------------------
    // Scoring Trend
    // --------------------------------------------------

    const scoringTrendCanvas = document.getElementById(
        "scoring-trend-chart"
    );

    if (scoringTrendCanvas) {
        new Chart(
            scoringTrendCanvas,
            {
                type: "line",

                data: {
                    labels: chartData.game_labels,

                    datasets: [
                        {
                            label: "Team Score",
                            data: chartData.team_scores,
                            tension: 0.25,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                        },
                    ],
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    interaction: {
                        mode: "index",
                        intersect: false,
                    },

                    scales: {
                        y: {
                            beginAtZero: true,

                            title: {
                                display: true,
                                text: "Points",
                            },
                        },
                    },
                },
            }
        );
    }


    // --------------------------------------------------
    // Team vs Opponent
    // --------------------------------------------------

    const scoreComparisonCanvas = document.getElementById(
        "score-comparison-chart"
    );

    if (scoreComparisonCanvas) {
        new Chart(
            scoreComparisonCanvas,
            {
                type: "bar",

                data: {
                    labels: chartData.game_labels,

                    datasets: [
                        {
                            label: "Team Score",
                            data: chartData.team_scores,
                        },
                        {
                            label: "Opponent Score",
                            data: chartData.opponent_scores,
                        },
                    ],
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    interaction: {
                        mode: "index",
                        intersect: false,
                    },

                    scales: {
                        y: {
                            beginAtZero: true,

                            title: {
                                display: true,
                                text: "Points",
                            },
                        },
                    },
                },
            }
        );
    }


    // --------------------------------------------------
    // Shooting Percentage Trends
    // --------------------------------------------------

    const shootingTrendCanvas = document.getElementById(
        "shooting-trend-chart"
    );

    if (shootingTrendCanvas) {
        new Chart(
            shootingTrendCanvas,
            {
                type: "line",

                data: {
                    labels: chartData.game_labels,

                    datasets: [
                        {
                            label: "FG%",
                            data: chartData.fg_percentages,
                            tension: 0.25,
                            pointRadius: 3,
                            pointHoverRadius: 5,
                        },
                        {
                            label: "2PT%",
                            data: chartData.two_point_percentages,
                            tension: 0.25,
                            pointRadius: 3,
                            pointHoverRadius: 5,
                        },
                        {
                            label: "3PT%",
                            data: chartData.three_point_percentages,
                            tension: 0.25,
                            pointRadius: 3,
                            pointHoverRadius: 5,
                        },
                        {
                            label: "FT%",
                            data: chartData.free_throw_percentages,
                            tension: 0.25,
                            pointRadius: 3,
                            pointHoverRadius: 5,
                        },
                    ],
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    interaction: {
                        mode: "index",
                        intersect: false,
                    },

                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 1,

                            title: {
                                display: true,
                                text: "Percentage",
                            },

                            ticks: {
                                callback: function(value) {
                                    return (
                                        value * 100
                                    ) + "%";
                                },
                            },
                        },
                    },

                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    if (context.raw === null) {
                                        return (
                                            context.dataset.label
                                            + ": —"
                                        );
                                    }

                                    return (
                                        context.dataset.label
                                        + ": "
                                        + (
                                            context.raw * 100
                                        ).toFixed(1)
                                        + "%"
                                    );
                                },
                            },
                        },
                    },
                },
            }
        );
    }
}


// --------------------------------------------------
// Win/Loss and Venue Comparisons
// --------------------------------------------------

const comparisonDataElement = document.getElementById(
    "season-comparison-data"
);

if (comparisonDataElement) {
    const comparisonData = JSON.parse(
        comparisonDataElement.textContent
    );


    // --------------------------------------------------
    // Win vs Loss
    // --------------------------------------------------

    const wins = comparisonData.by_result.WIN;
    const losses = comparisonData.by_result.LOSS;

    const resultComparisonCanvas = document.getElementById(
        "result-comparison-chart"
    );

    if (resultComparisonCanvas) {
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
                        },
                        {
                            label: "RPG",
                            data: [
                                wins.rebounds_per_game,
                                losses.rebounds_per_game,
                            ],
                        },
                        {
                            label: "APG",
                            data: [
                                wins.assists_per_game,
                                losses.assists_per_game,
                            ],
                        },
                        {
                            label: "TO/G",
                            data: [
                                wins.turnovers_per_game,
                                losses.turnovers_per_game,
                            ],
                        },
                    ],
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    interaction: {
                        mode: "index",
                        intersect: false,
                    },

                    scales: {
                        y: {
                            beginAtZero: true,
                        },
                    },
                },
            }
        );
    }


    // --------------------------------------------------
    // Performance by Venue
    // --------------------------------------------------

    const home = comparisonData.by_venue.HOME;
    const away = comparisonData.by_venue.AWAY;
    const neutral = comparisonData.by_venue.NEUTRAL;

    const venueComparisonCanvas = document.getElementById(
        "venue-comparison-chart"
    );

    if (venueComparisonCanvas) {
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
                        },
                        {
                            label: "RPG",
                            data: [
                                home.rebounds_per_game,
                                away.rebounds_per_game,
                                neutral.rebounds_per_game,
                            ],
                        },
                        {
                            label: "APG",
                            data: [
                                home.assists_per_game,
                                away.assists_per_game,
                                neutral.assists_per_game,
                            ],
                        },
                        {
                            label: "TO/G",
                            data: [
                                home.turnovers_per_game,
                                away.turnovers_per_game,
                                neutral.turnovers_per_game,
                            ],
                        },
                    ],
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    interaction: {
                        mode: "index",
                        intersect: false,
                    },

                    scales: {
                        y: {
                            beginAtZero: true,
                        },
                    },
                },
            }
        );
    }
}


// --------------------------------------------------
// Player Scoring Comparison
// --------------------------------------------------

const playerScoringDataElement = document.getElementById(
    "season-player-scoring-data"
);

if (playerScoringDataElement) {
    const playerScoringData = JSON.parse(
        playerScoringDataElement.textContent
    );

    const playerScoringCanvas = document.getElementById(
        "player-scoring-chart"
    );

    if (playerScoringCanvas) {
        new Chart(
            playerScoringCanvas,
            {
                type: "bar",

                data: {
                    labels: playerScoringData.map(
                        player => player.player_name
                    ),

                    datasets: [
                        {
                            label: "PPG",

                            data: playerScoringData.map(
                                player => player.points_per_game
                            ),
                        },
                    ],
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,

                    indexAxis: "y",

                    scales: {
                        x: {
                            beginAtZero: true,

                            title: {
                                display: true,
                                text: "Points Per Game",
                            },
                        },
                    },

                    plugins: {
                        legend: {
                            display: false,
                        },

                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return (
                                        context.raw.toFixed(1)
                                        + " PPG"
                                    );
                                },
                            },
                        },
                    },
                },
            }
        );
    }
}