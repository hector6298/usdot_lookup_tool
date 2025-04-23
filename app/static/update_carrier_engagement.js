const checkboxes = document.querySelectorAll('.checkbox-track');
const submitButton = document.getElementById('submit-button');
const revertButton = document.getElementById('revert-button');
let initialStates = {};

document.addEventListener("DOMContentLoaded", () => {
    // Save initial states of checkboxes
    checkboxes.forEach(checkbox => {
        initialStates[checkbox.dataset.usdot + '-' + checkbox.dataset.field] = checkbox.checked;
    });

    // Track changes and enable/disable buttons
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            const hasChanges = Array.from(checkboxes).some(cb => 
                cb.checked !== initialStates[cb.dataset.usdot + '-' + cb.dataset.field]
            );
            submitButton.disabled = !hasChanges;
            revertButton.disabled = !hasChanges;
        });
    });

    // Revert button functionality
    revertButton.addEventListener('click', () => {
        checkboxes.forEach(checkbox => {
            checkbox.checked = initialStates[checkbox.dataset.usdot + '-' + checkbox.dataset.field];
        });
        submitButton.disabled = true;
        revertButton.disabled = true;
    });

    // Submit button functionality
    submitButton.addEventListener('click', () => {
        const changes = Array.from(checkboxes)
            .filter(cb => cb.checked !== initialStates[cb.dataset.usdot + '-' + cb.dataset.field])
            .map(cb => ({
                usdot: cb.dataset.usdot,
                field: cb.dataset.field,
                value: cb.checked
            }));
        
        if (changes.length === 0) {
            alert('No changes to submit.');
            return;
        }

        console.log(JSON.stringify({changes}));
        // Send changes to the server (example using fetch)
        fetch('/update_carrier_interests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({changes})
        }).then(response => {
            if (response.ok) {
                // Update initial states after successful submission
                checkboxes.forEach(checkbox => {
                    initialStates[checkbox.dataset.usdot + '-' + checkbox.dataset.field] = checkbox.checked;
                });
                submitButton.disabled = true;
                revertButton.disabled = true;
            } else {
                console.log('Failed to submit changes:', response);
                response.json().then(errorData => {
                    alert(`Failed to submit changes: ${errorData.message || 'Unknown error'}`);
                }).catch(() => {
                    alert('Failed to submit changes and could not parse error response.');
                });
            }
        });
    });

});