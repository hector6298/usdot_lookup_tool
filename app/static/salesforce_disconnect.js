// Function to disconnect from Salesforce
async function disconnectSalesforce() {
    if (confirm('Are you sure you want to disconnect from Salesforce?')) {
        try {
            const response = await fetch('/salesforce/disconnect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            
            if (response.ok) {
                // Reload the page to update the UI
                window.location.reload();
            } else {
                alert('Failed to disconnect from Salesforce. Please try again.');
            }
        } catch (error) {
            console.error('Error disconnecting from Salesforce:', error);
            alert('Error disconnecting from Salesforce. Please try again.');
        }
    }
}