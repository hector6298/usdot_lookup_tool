document.addEventListener('DOMContentLoaded', function() {
    // Get the current number of mappings from existing table rows
    let mappingCounter = document.querySelectorAll('#mappingTableBody tr').length;
    
    // Check for success/error messages in URL parameters and show popup
    checkForNotifications();
    
    // Add new mapping row
    document.getElementById('addMappingBtn').addEventListener('click', function() {
        const template = document.getElementById('newMappingRowTemplate');
        const newRow = template.content.cloneNode(true);
        
        // Update the mapping counter
        mappingCounter++;
        
        // Update all name attributes and data attributes
        const row = newRow.querySelector('tr');
        row.setAttribute('data-mapping-id', mappingCounter);
        
        // Update all input/select names
        const inputs = newRow.querySelectorAll('input, select');
        inputs.forEach(input => {
            const name = input.getAttribute('name');
            if (name) {
                input.setAttribute('name', name + mappingCounter);
            }
        });
        
        // Add to table
        document.getElementById('mappingTableBody').appendChild(newRow);
        
        // Update total mappings counter
        updateTotalMappings();
        
        // Add event listeners to new row
        addRowEventListeners(row);
    });
    
    // Reset to defaults
    document.getElementById('resetToDefaultBtn').addEventListener('click', function() {
        if (confirm('Are you sure you want to reset to default mappings? This will remove all custom mappings.')) {
            fetch('/salesforce/field-mapping/reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.detail === 'Default mappings created successfully.') {
                    location.reload();
                } else {
                    alert('Error resetting mappings: ' + data.detail);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error resetting mappings');
            });
        }
    });
    
    // Function to add event listeners to a row
    function addRowEventListeners(row) {
        // Remove mapping button
        const removeBtn = row.querySelector('.remove-mapping-btn');
        if (removeBtn) {
            removeBtn.addEventListener('click', function() {
                row.remove();
                updateTotalMappings();
            });
        }
        
        // Carrier field change handler
        const carrierSelect = row.querySelector('.carrier-field-select');
        if (carrierSelect) {
            carrierSelect.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                const fieldType = selectedOption.getAttribute('data-type') || 'text';
                const typeSelect = row.querySelector('.field-type-select');
                if (typeSelect) {
                    typeSelect.value = fieldType;
                }
            });
        }
        
        // Salesforce field change handler
        const sfSelect = row.querySelector('.salesforce-field-select');
        const customInput = row.querySelector('.custom-field-input');
        if (sfSelect && customInput) {
            sfSelect.addEventListener('change', function() {
                if (this.value === '') {
                    customInput.style.display = 'block';
                    customInput.required = true;
                } else {
                    customInput.style.display = 'none';
                    customInput.required = false;
                    customInput.value = '';
                }
            });
        }
    }
    
    // Add event listeners to existing rows
    document.querySelectorAll('#mappingTableBody tr').forEach(addRowEventListeners);
    
    // Update total mappings counter
    function updateTotalMappings() {
        const totalRows = document.querySelectorAll('#mappingTableBody tr').length;
        document.getElementById('totalMappings').value = totalRows;
    }
    
    // Form submission handler
    document.getElementById('fieldMappingForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate that all rows have both carrier field and salesforce field
        const rows = document.querySelectorAll('#mappingTableBody tr');
        let isValid = true;
        
        rows.forEach(row => {
            const carrierField = row.querySelector('.carrier-field-select').value;
            const salesforceField = row.querySelector('.salesforce-field-select').value;
            const customField = row.querySelector('.custom-field-input').value;
            
            if (!carrierField || (!salesforceField && !customField)) {
                isValid = false;
            }
        });
        
        if (!isValid) {
            alert('Please fill in all carrier fields and salesforce fields.');
            return;
        }
        
        // Submit the form
        this.submit();
    });
    
    // Function to check for success/error notifications in URL parameters
    function checkForNotifications() {
        const urlParams = new URLSearchParams(window.location.search);
        const success = urlParams.get('success');
        const error = urlParams.get('error');
        
        if (success === '1') {
            Notifications.success('Field mappings saved successfully!');
            // Clean the URL by removing the success parameter
            cleanUrl();
        } else if (error === '1') {
            Notifications.error('Error saving field mappings. Please try again.');
            // Clean the URL by removing the error parameter
            cleanUrl();
        }
    }
    
    // Function to clean URL parameters
    function cleanUrl() {
        const url = new URL(window.location);
        url.searchParams.delete('success');
        url.searchParams.delete('error');
        window.history.replaceState({}, document.title, url.toString());
    }
});