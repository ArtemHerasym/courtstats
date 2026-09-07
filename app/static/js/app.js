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
                // Theme still works for this page
                // if browser storage is unavailable.
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


    // Follow operating-system theme changes only when
    // the user has not manually selected a preference.

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
                        if (
                            mobileQuery.matches
                        ) {
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


                // Provides a visual DNP state
                // without changing backend behavior.
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