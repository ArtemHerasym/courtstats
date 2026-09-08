document.addEventListener("DOMContentLoaded", () => {
    document.documentElement.classList.add(
        "js-ready"
    );


    // ==================================================
    // Theme
    // ==================================================

    const root = document.documentElement;

    const themeButtons = document.querySelectorAll(
        "[data-theme-toggle]"
    );


    const getCurrentTheme = () => {
        return (
            root.dataset.theme === "dark"
                ? "dark"
                : "light"
        );
    };


    const updateThemeControls = () => {
        const currentTheme = getCurrentTheme();

        const nextTheme = (
            currentTheme === "dark"
                ? "light"
                : "dark"
        );

        themeButtons.forEach((button) => {
            const label = button.querySelector(
                "[data-theme-label]"
            );

            if (label) {
                label.textContent = (
                    nextTheme === "dark"
                        ? "Dark mode"
                        : "Light mode"
                );
            }

            button.setAttribute(
                "aria-label",
                `Switch to ${nextTheme} mode`
            );

            button.setAttribute(
                "title",
                `Switch to ${nextTheme} mode`
            );
        });
    };


    const setTheme = (
        theme,
        persist = true
    ) => {
        root.dataset.theme = theme;

        if (persist) {
            try {
                localStorage.setItem(
                    "courtstats-theme",
                    theme
                );
            } catch (error) {
                // Storage may be unavailable.
            }
        }

        updateThemeControls();

        window.dispatchEvent(
            new CustomEvent(
                "courtstats:themechange",
                {
                    detail: {
                        theme,
                    },
                }
            )
        );
    };


    themeButtons.forEach((button) => {
        button.addEventListener(
            "click",
            () => {
                const nextTheme = (
                    getCurrentTheme() === "dark"
                        ? "light"
                        : "dark"
                );

                setTheme(nextTheme);
            }
        );
    });


    updateThemeControls();


    const colorSchemeQuery = window.matchMedia(
        "(prefers-color-scheme: dark)"
    );


    const handleSystemThemeChange = (event) => {
        let savedTheme = null;

        try {
            savedTheme = localStorage.getItem(
                "courtstats-theme"
            );
        } catch (error) {
            savedTheme = null;
        }

        if (
            savedTheme === "light"
            || savedTheme === "dark"
        ) {
            return;
        }

        setTheme(
            event.matches
                ? "dark"
                : "light",
            false
        );
    };


    colorSchemeQuery.addEventListener(
        "change",
        handleSystemThemeChange
    );


    // ==================================================
    // Mobile navigation
    // ==================================================

    const navToggle = document.querySelector(
        "[data-nav-toggle]"
    );

    const navPanel = document.querySelector(
        "[data-nav-panel]"
    );


    if (navToggle && navPanel) {
        const mobileQuery = window.matchMedia(
            "(max-width: 760px)"
        );


        const setNavigationOpen = (open) => {
            navPanel.classList.toggle(
                "is-open",
                open
            );

            navToggle.setAttribute(
                "aria-expanded",
                String(open)
            );
        };


        navToggle.addEventListener(
            "click",
            () => {
                const currentlyOpen = (
                    navToggle.getAttribute(
                        "aria-expanded"
                    ) === "true"
                );

                setNavigationOpen(
                    !currentlyOpen
                );
            }
        );


        navPanel
            .querySelectorAll("a")
            .forEach((link) => {
                link.addEventListener(
                    "click",
                    () => {
                        if (mobileQuery.matches) {
                            setNavigationOpen(
                                false
                            );
                        }
                    }
                );
            });


        document.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.key === "Escape"
                    && navToggle.getAttribute(
                        "aria-expanded"
                    ) === "true"
                ) {
                    setNavigationOpen(false);
                    navToggle.focus();
                }
            }
        );


        mobileQuery.addEventListener(
            "change",
            () => {
                setNavigationOpen(false);
            }
        );
    }


    // ==================================================
    // Date input formatting
    // ==================================================

    const formatDateDigits = (
        value,
        appendBoundarySlash = true
    ) => {
        const digits = value
            .replace(/\D/g, "")
            .slice(0, 8);

        if (digits.length <= 2) {
            if (
                digits.length === 2
                && appendBoundarySlash
            ) {
                return `${digits}/`;
            }

            return digits;
        }

        if (digits.length <= 4) {
            const month = digits.slice(
                0,
                2
            );

            const day = digits.slice(
                2,
                4
            );

            if (
                digits.length === 4
                && appendBoundarySlash
            ) {
                return `${month}/${day}/`;
            }

            return `${month}/${day}`;
        }

        return (
            `${digits.slice(0, 2)}/`
            + `${digits.slice(2, 4)}/`
            + digits.slice(4, 8)
        );
    };


    document
        .querySelectorAll(
            "[data-date-input]"
        )
        .forEach((input) => {
            input.addEventListener(
                "input",
                (event) => {
                    const isDeleting = (
                        event.inputType
                        && event.inputType.startsWith(
                            "delete"
                        )
                    );

                    input.value = formatDateDigits(
                        input.value,
                        !isDeleting
                    );
                }
            );
        });


    // ==================================================
    // Player picker
    // ==================================================

    const playerPicker = document.querySelector(
        "[data-player-picker]"
    );


    if (playerPicker) {
        const searchInput = (
            playerPicker.querySelector(
                "[data-player-search]"
            )
        );

        const playerIdInput = (
            playerPicker.querySelector(
                "[data-player-id]"
            )
        );

        const resultsContainer = (
            playerPicker.querySelector(
                "[data-player-results]"
            )
        );

        const statusText = (
            playerPicker.querySelector(
                "[data-player-search-status]"
            )
        );

        const selectedCard = (
            playerPicker.querySelector(
                "[data-player-selected]"
            )
        );

        const selectedName = (
            playerPicker.querySelector(
                "[data-player-selected-name]"
            )
        );

        const clearButton = (
            playerPicker.querySelector(
                "[data-player-clear]"
            )
        );

        let searchTimer = null;


        const clearResults = () => {
            resultsContainer.replaceChildren();
        };


        const choosePlayer = (
            playerId,
            playerName
        ) => {
            playerIdInput.value = String(
                playerId
            );

            selectedName.textContent = (
                playerName
            );

            selectedCard.hidden = false;

            searchInput.value = "";

            clearResults();

            statusText.textContent = (
                "Player selected."
            );
        };


        const renderPlayers = (players) => {
            clearResults();

            if (players.length === 0) {
                statusText.textContent = (
                    "No matching players found. "
                    + "You can create a new Player."
                );

                return;
            }

            statusText.textContent = (
                `${players.length} matching `
                + "player"
                + (
                    players.length === 1
                        ? ""
                        : "s"
                )
                + " found."
            );


            players.forEach((player) => {
                const button = (
                    document.createElement(
                        "button"
                    )
                );

                button.type = "button";

                button.className = (
                    "button button-secondary"
                );

                const playerName = (
                    player.display_name
                    || player.full_name
                );

                button.textContent = playerName;

                if (
                    player.display_name
                    && player.display_name
                    !== player.full_name
                ) {
                    button.textContent += (
                        ` — ${player.full_name}`
                    );
                }

                button.addEventListener(
                    "click",
                    () => {
                        choosePlayer(
                            player.id,
                            playerName
                        );
                    }
                );

                resultsContainer.appendChild(
                    button
                );
            });
        };


        const runSearch = async () => {
            const query = (
                searchInput.value.trim()
            );

            if (!query) {
                clearResults();

                statusText.textContent = (
                    "Search the global CourtStats "
                    + "player directory."
                );

                return;
            }

            statusText.textContent = (
                "Searching..."
            );

            try {
                const response = await fetch(
                    (
                        "/app/players/search?q="
                        + encodeURIComponent(
                            query
                        )
                    ),
                    {
                        headers: {
                            "Accept":
                                "application/json",
                        },
                    }
                );

                if (!response.ok) {
                    throw new Error(
                        "Player search failed."
                    );
                }

                const players = (
                    await response.json()
                );

                renderPlayers(players);

            } catch (error) {
                clearResults();

                statusText.textContent = (
                    "Player search is unavailable. "
                    + "Please try again."
                );
            }
        };


        searchInput.addEventListener(
            "input",
            () => {
                window.clearTimeout(
                    searchTimer
                );

                searchTimer = (
                    window.setTimeout(
                        runSearch,
                        180
                    )
                );
            }
        );


        if (clearButton) {
            clearButton.addEventListener(
                "click",
                () => {
                    playerIdInput.value = "";
                    selectedCard.hidden = true;

                    searchInput.focus();

                    statusText.textContent = (
                        "Search for another Player."
                    );
                }
            );
        }


        const createPlayerLink = (
            playerPicker.querySelector(
                "[data-create-player-link]"
            )
        );

        const seasonSelect = (
            document.querySelector(
                'select[name="season_id"]'
            )
        );


        if (
            createPlayerLink
            && seasonSelect
        ) {
            const updateCreatePlayerLink = () => {
                const baseHref = (
                    createPlayerLink.dataset
                        .baseHref
                );

                const url = new URL(
                    baseHref,
                    window.location.origin
                );

                if (seasonSelect.value) {
                    url.searchParams.set(
                        "season_id",
                        seasonSelect.value
                    );
                }

                createPlayerLink.href = (
                    url.pathname
                    + url.search
                );
            };


            seasonSelect.addEventListener(
                "change",
                updateCreatePlayerLink
            );

            updateCreatePlayerLink();
        }
    }


    // ==================================================
    // Add New Opponent fields
    // ==================================================

    const opponentSelect = document.querySelector(
        "#opponent_team_id"
    );

    const newOpponentFields = document.querySelector(
        "#new-opponent-fields"
    );


    if (
        opponentSelect
        && newOpponentFields
    ) {
        const updateOpponentFields = () => {
            newOpponentFields.hidden = (
                opponentSelect.value !== "new"
            );
        };


        opponentSelect.addEventListener(
            "change",
            updateOpponentFields
        );


        updateOpponentFields();
    }


    // ==================================================
    // Player participation / DNP behavior
    // ==================================================

    document
        .querySelectorAll(
            ".participation-select"
        )
        .forEach((select) => {
            const row = select.closest(
                ".stats-row"
            );

            if (!row) {
                return;
            }

            const statInputs = (
                row.querySelectorAll(
                    ".stats-input"
                )
            );


            const updateParticipationState = () => {
                const isDnp = (
                    select.value
                    === "DID_NOT_PLAY"
                );

                row.classList.toggle(
                    "is-dnp",
                    isDnp
                );

                statInputs.forEach((input) => {
                    if (isDnp) {
                        input.value = "0";
                    }

                    input.readOnly = isDnp;

                    input.setAttribute(
                        "aria-disabled",
                        String(isDnp)
                    );
                });
            };


            select.addEventListener(
                "change",
                updateParticipationState
            );


            updateParticipationState();
        });
});