document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('salesforceSetupForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const sfDomain = formData.get('sf_domain');
        
        if (!sfDomain.trim()) {
            alert('Please enter your Salesforce domain.');
            return;
        }
        
        try {
            const response = await fetch('/salesforce/setup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ sf_domain: sfDomain })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                alert('Salesforce domain saved successfully! You can now connect to Salesforce.');
                window.location.href = '/salesforce/connect';
            } else {
                alert(result.detail || 'Failed to save Salesforce domain.');
            }
        } catch (error) {
            alert('An error occurred. Please try again.');
            console.error('Error:', error);
        }
    });
});