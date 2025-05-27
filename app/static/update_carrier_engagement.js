export const Engagement = {
    initialStates: {},

    trackChanges: function () {
        const inputs = document.querySelectorAll(".checkbox-track, .form-control[data-field='carrier_follow_up_by_date']");
        const submitButton = document.getElementById("submit-button");
        const revertButton = document.getElementById("revert-button");

        inputs.forEach((input) => {
            input.addEventListener("change", () => {
                const hasChanges = Array.from(inputs).some((input) => {
                    const key = input.dataset.usdot + "-" + input.dataset.field;
                    return input.type === "checkbox"
                        ? input.checked !== Engagement.initialStates[key]
                        : input.value !== Engagement.initialStates[key];
                });
                submitButton.disabled = !hasChanges;
                revertButton.disabled = !hasChanges;
            });
        });
    },

    revertChanges: function () {
        const inputs = document.querySelectorAll(".checkbox-track, .form-control[data-field='carrier_follow_up_by_date']");
        inputs.forEach((input) => {
            const key = input.dataset.usdot + "-" + input.dataset.field;
            if (input.type === "checkbox") {
                input.checked = Engagement.initialStates[key];
            } else {
                input.value = Engagement.initialStates[key];
            }
        });
        document.getElementById("submit-button").disabled = true;
        document.getElementById("revert-button").disabled = true;
    },

    submitChanges: function () {
        const inputs = document.querySelectorAll(".checkbox-track, .form-control[data-field='carrier_follow_up_by_date']");
        const changes = Array.from(inputs)
            .filter((input) => {
                const key = input.dataset.usdot + "-" + input.dataset.field;
                return input.type === "checkbox"
                    ? input.checked !== Engagement.initialStates[key]
                    : input.value !== Engagement.initialStates[key];
            })
            .map((input) => ({
                usdot: input.dataset.usdot,
                field: input.dataset.field,
                value: input.type === "checkbox" ? input.checked : input.value,
            }));

        if (changes.length === 0) {
            alert("No changes to submit.");
            return;
        }

        fetch("/data/update/carrier_interests", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ changes }),
        })
            .then((response) => {
                if (response.ok) {
                    inputs.forEach((input) => {
                        const key = input.dataset.usdot + "-" + input.dataset.field;
                        if (input.type === "checkbox") {
                            Engagement.initialStates[key] = input.checked;
                        } else {
                            Engagement.initialStates[key] = input.value;
                        }
                    });
                    document.getElementById("submit-button").disabled = true;
                    document.getElementById("revert-button").disabled = true;
                } else {
                    alert("Failed to submit changes.");
                }
            })
            .catch((error) => console.error("Error submitting changes:", error));
    },

    reinitializeInputs: function () {
        const inputs = document.querySelectorAll(".checkbox-track, .form-control[data-field='carrier_follow_up_by_date']");
        inputs.forEach((input) => {
            const key = input.dataset.usdot + "-" + input.dataset.field;
            if (!(key in Engagement.initialStates)) {
                Engagement.initialStates[key] = input.type === "checkbox" ? input.checked : input.value;
                input.addEventListener("change", () => {
                    const hasChanges = Array.from(inputs).some((input) => {
                        const key = input.dataset.usdot + "-" + input.dataset.field;
                        return input.type === "checkbox"
                            ? input.checked !== Engagement.initialStates[key]
                            : input.value !== Engagement.initialStates[key];
                    });
                    document.getElementById("submit-button").disabled = !hasChanges;
                    document.getElementById("revert-button").disabled = !hasChanges;
                });
            }
        });
    },

    init: function () {
        const inputs = document.querySelectorAll(".checkbox-track, .form-control[data-field='carrier_follow_up_by_date']");
        inputs.forEach((input) => {
            const key = input.dataset.usdot + "-" + input.dataset.field;
            Engagement.initialStates[key] = input.type === "checkbox" ? input.checked : input.value;
        });

        document.getElementById("revert-button").addEventListener("click", Engagement.revertChanges);
        document.getElementById("submit-button").addEventListener("click", Engagement.submitChanges);

        Engagement.trackChanges();
    },
};

document.addEventListener("DOMContentLoaded", Engagement.init);