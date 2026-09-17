async function loadSessionStatus() {
    const prefix = "auth";
    const token = localStorage.getItem("access_token");
    console.log("Token exists:", !!token);

    try {
        const response = await fetch(`/${prefix}/session-status`, {
            method: "GET",
            credentials: "include",
            headers: {
                ...(token ? { Authorization: `Bearer ${token}` } : {})
            }
        });

        console.log("Session status response:", response.status);

        const el = document.querySelector(".user-status .username");
        if (!el) {
            console.warn("Element .user-status .username not found on page");
            return;
        }

        if (!response.ok) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");

            el.textContent = "unknown";
            el.classList.add("logged-out");
            el.classList.remove("logged-in");
            return;
        }

        const data = await response.json();
        console.log("Session data received:", data);

        if (data.data.logged_in && data.data.email) {
            el.textContent = data.data.email;
            el.classList.add("logged-in");
            el.classList.remove("logged-out");
        } else {
            el.textContent = "unknown";
            el.classList.add("logged-out");
            el.classList.remove("logged-in");
        }

    } catch (error) {
        console.error("Error loading session status:", error);
        const el = document.querySelector(".user-status .username");
        if (el) {
            el.textContent = "unknown";
            el.classList.add("logged-out");
            el.classList.remove("logged-in");
        }
    }
}

/**
 * Call this from session.js in your logout submit branch:
 * window.applyImmediateLogoutEffects();
 */
function applyImmediateLogoutEffects() {
    const el = document.querySelector(".user-status .username");
    if (el) {
        el.textContent = "unknown";
        el.classList.add("logged-out");
        el.classList.remove("logged-in");
    }

    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    sessionStorage.removeItem("index_page_state_v1");

    if (typeof window.clearIndexUI === "function") {
        window.clearIndexUI();
    }
}

window.loadSessionStatus = loadSessionStatus;
window.applyImmediateLogoutEffects = applyImmediateLogoutEffects;

document.addEventListener("DOMContentLoaded", () => {
    loadSessionStatus();
});