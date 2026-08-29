document.addEventListener("DOMContentLoaded", () => {
    document.documentElement.classList.add("js-ready");

    // Add New Opponent fields
    const opponentSelect = document.querySelector("#opponent_team_id");
    const newOpponentFields = document.querySelector("#new-opponent-fields");

    if (opponentSelect && newOpponentFields) {
        const updateOpponentFields = () => {
            newOpponentFields.hidden = opponentSelect.value !== "new";
        };

        opponentSelect.addEventListener("change", updateOpponentFields);
        updateOpponentFields();
    }

    // Player participation / DNP behavior
    document.querySelectorAll(".participation-select").forEach((select) => {
        const row = select.closest(".stats-row");

        if (!row) {
            return;
        }

        const statInputs = row.querySelectorAll(".stats-input");

        const updateParticipationState = () => {
            const isDnp = select.value === "DID_NOT_PLAY";

            statInputs.forEach((input) => {
                if (isDnp) {
                    input.value = "0";
                }

                input.readOnly = isDnp;
                input.setAttribute("aria-disabled", String(isDnp));
            });
        };

        select.addEventListener("change", updateParticipationState);
        updateParticipationState();
    });
});