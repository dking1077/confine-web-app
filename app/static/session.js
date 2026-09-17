const buttons = document.querySelectorAll(".mode-btn");
const form = document.getElementById("session_form");
const authResults = document.getElementById("auth_results");

const emailInput = document.getElementById("email_input");
const passwordInput = document.getElementById("password_input");

let currentMode = "login";
let prefix = "auth";

/* ---------------- MODE HANDLER ---------------- */

function setAuthMode(mode) {
    currentMode = mode;

    emailInput.required = mode !== "logout";
    passwordInput.required = mode !== "logout";

    console.log("[MODE]", currentMode);
}

/* ---------------- FORM SUBMIT ---------------- */

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = emailInput.value;
    const password = passwordInput.value;

    try {
        const token = localStorage.getItem("access_token");

        const options = {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json",
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
        };

        if (currentMode !== "logout") {
            options.body = JSON.stringify({ email, password });
        }

        const response = await fetch(`/${prefix}/${currentMode}`, options);
        const raw = await response.text();

        let data;
        try {
            data = JSON.parse(raw);
        } catch {
            throw new Error("Invalid JSON from backend");
        }

        if (response.ok) {
            if (currentMode === "login") {
                localStorage.setItem("access_token", data.data.access_token);
                localStorage.setItem("refresh_token", data.data.refresh_token);

                if (typeof window.loadSessionStatus === "function") {
                    await window.loadSessionStatus();
                }
            }

            if (currentMode === "logout") {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");

                if (typeof window.applyImmediateLogoutEffects === "function") {
                    window.applyImmediateLogoutEffects();
                }
            }

            authResults.innerHTML =
                `<span class="success">${data.code} | ${data.message}</span>`;
        } else {
            authResults.innerHTML =
                `<span class="error">${data.code ?? currentMode} | ${data.message ?? "failed"}</span>`;
        }

        form.reset();
    } catch (err) {
        authResults.innerHTML =
            `<span class="error">Error: ${err.message}</span>`;
    }
});

/* ---------------- MODE SWITCH ---------------- */

buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
        buttons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        setAuthMode(btn.dataset.mode);

        console.log("[MODE SWITCH]", btn.dataset.mode);
    });
});

/* ---------------- INITIAL STATE ---------------- */

setAuthMode(currentMode);