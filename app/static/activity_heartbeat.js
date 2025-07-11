// --- Inactivity Timer + Heartbeat Mechanism ---

const INACTIVITY_LIMIT = 15 * 60 * 1000; // 15 minutes in ms
const HEARTBEAT_INTERVAL = 5 * 60 * 1000; // 5 minutes in ms

let inactivityTimeout;

// Reset inactivity timer on user activity
function resetInactivityTimer() {
    clearTimeout(inactivityTimeout);
    inactivityTimeout = setTimeout(() => {
        // Optionally show a modal before logout
        window.location.href = "/logout";
    }, INACTIVITY_LIMIT);
}

// Listen for user activity
["mousemove", "keydown", "mousedown", "touchstart"].forEach(evt =>
    document.addEventListener(evt, resetInactivityTimer)
);

// Start the timer on page load
resetInactivityTimer();

// Heartbeat: ping the server every HEARTBEAT_INTERVAL
setInterval(async () => {
    try {
        const resp = await fetch("/session/heartbeat");
        if (resp.status === 401) {
            window.location.href = "/login";
        }
    } catch (e) {
        // Optionally handle network errors
        // console.error("Heartbeat failed", e);
    }
}, HEARTBEAT_INTERVAL);